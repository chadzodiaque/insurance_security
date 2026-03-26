import tink
import tink_fpe
import json
from tink import cleartext_keyset_handle, JsonKeysetReader
from tink_fpe import FpeParams, UnknownCharacterStrategy
import io,secrets, base64
import hashlib
import hvac
from odoo import tools

from .cryptocache import KeyCache

class Crypto:

    def __init__(self):
        
        # Enregistrement de Tink FPE avec le runtime Tink
        tink_fpe.register()

        self.params = FpeParams(strategy=UnknownCharacterStrategy.SKIP)

        # 🔐 Connexion Vault
        config = tools.config
        self.vault = hvac.Client(
            url=config.get('vault_url'),
            token=config.get('vault_token')
        )

        if not self.vault.is_authenticated():
            raise Exception("Vault authentication failed")

    def generate_tweak(self):
        """Génère un tweak de 7 bytes encodé en base64"""
        tweak_bytes = secrets.token_bytes(7)
        return base64.b64encode(tweak_bytes).decode()

    def get_tweak_bytes(self, reference):
        return base64.b64decode(reference.encode())
   
    def create_keyset(self):
        """Création de la keyset."""

        # Spécifier le modèle de clé à utiliser. Dans cet exemple, nous voulons une clé FF3-1 de 256 bits
        # qui peut gérer les caractères alphanumériques
        key_template = tink_fpe.fpe_key_templates.FPE_FF31_256_ALPHANUMERIC

        # Créer un keyset
        keyset_handle = tink.new_keyset_handle(key_template)

        # buffer mémoire (au lieu d’un fichier)
        output = io.StringIO()
        cleartext_keyset_handle.write(
            tink.JsonKeysetWriter(output),
            keyset_handle
        )

        keyset_json = json.loads(output.getvalue())
        
        # Stocker dans Vault
        self.vault.secrets.kv.v2.create_or_update_secret(
            path=f"odoo/InsuranceSecurity",
            secret={"keyset": keyset_json}
        )

        return True
    
    def get_keyset(self):
        """ Récupère une clé depuis Vault.

        :param str reference: l'ID de l'utilisateur pour lequel la clé est stockée.
        :return dict: la clé stockée dans Vault.
        :raises: Exception si la clé n'existe pas dans Vault.
        """
        secret = self.vault.secrets.kv.v2.read_secret_version(
            path=f"odoo/InsuranceSecurity",
            raise_on_deleted_version=True
        )
        return secret['data']['data']['keyset']

    """ def delete_keyset(self, reference):

        #Supprime la clé FPE stockée dans Vault pour l'utilisateur dont l'ID est spécifié par le paramètre reference.

        #:param str reference: l'ID de l'utilisateur pour lequel la clé est stockée.
        #:raises: Exception si la suppression de la clé échoue.
       
        try:
            # suppression complète (KV v2)
            self.vault.secrets.kv.v2.delete_metadata_and_all_versions(
                path=f"users/{reference}"
            )
            print(f"Clé supprimée pour {reference}")

        except Exception as e:
            print(f"Erreur Vault: {e}") """
                

    
    def encrypt_data(self, data, reference):
        """Chiffre les données avec FPE.

        Les données sont chiffrées en utilisant la clé FPE stockée dans Vault
        pour l'utilisateur dont l'ID est spécifié par le paramètre reference.
        """
        try:
            # Chiffrement des données
            keyset_key = KeyCache.get_key(crypto=self)
            if keyset_key :
                keyset_handle = cleartext_keyset_handle.read(
                    tink.JsonKeysetReader(json.dumps(keyset_key))
                )
                fpe = keyset_handle.primitive(tink_fpe.Fpe)
                params = FpeParams(
                    strategy=UnknownCharacterStrategy.SKIP,
                    tweak=self.get_tweak_bytes(reference)
                )
                return fpe.encrypt(data.encode(), params).decode()
            else:
                return None
        except tink.TinkError as e:
            print(f"Erreur lors du chiffrement des données : {e}")
            return None
    
    def decrypt_data(self, encrypted_data, reference):
        """Déchiffre les données avec FPE."""
        # Les données chiffrées sont stockées sous forme de string
        try:
            # Récupération de la clé FPE stockée dans Vault pour l'utilisateur
            keyset_key = KeyCache.get_key(crypto=self)
            if keyset_key:
                keyset_handle = cleartext_keyset_handle.read(
                    tink.JsonKeysetReader(json.dumps(keyset_key))
                )
                fpe = keyset_handle.primitive(tink_fpe.Fpe)
                  # Déchiffrement des données
                params = FpeParams(
                    strategy=UnknownCharacterStrategy.SKIP,
                    tweak=self.get_tweak_bytes(reference)
                )
                decrypted = fpe.decrypt(encrypted_data.encode(), params).decode()
            return decrypted 
        except tink.TinkError as e:
            # Si une erreur se produit, afficher le message d'erreur
            print(f"Erreur lors du déchiffrement des données : {e}")
            return None

