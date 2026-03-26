from odoo import fields, models, api, _
from ..utils.cryptofpe import Crypto
from odoo.exceptions import ValidationError

import logging
import re
import uuid
import secrets

_logger = logging.getLogger(__name__)

class InsuranceClients(models.Model):

    _name = "insurance.security.clients"
    _description = "Client"

    name = fields.Char(string='Nom complet', required=True)
    related_partner = fields.Many2one('res.partner', string='Related User', required=True)
    sex = fields.Selection([('male', 'Male'), ('female', 'Female')], required=True)
    email = fields.Char(string="Email", copy=False, required=True)
    phone = fields.Char(string='Numero de telephone', copy=False, required=True)
    adress = fields.Char(string='Adresse', required=True)
    country = fields.Char(string='Pays', required=True)
    nationality = fields.Char(string='Nationalité ', required=True)
    proofs = fields.Many2many(
        'ir.attachment', 
        string='Preuves ', 
        help=' Insérer les documents suivants : Carte d\'identité ou passport, Carte grise(s), Permis de conduire, TVM et Attestion de controle technique',
        readonly=True
    )
    
    """ Relations de models"""
    claims_ids = fields.One2many("insurance.security.claims", "client_id", string="Mes reclamations")
    policy_ids = fields.One2many("insurance.security.policy", "client_id", string="Mes polices d'assurance ")
    cars_ids = fields.One2many("insurance.security.cars", "client_id", string="Mes voitures enregistrés")

    reference = fields.Char(string="Key Reference")
    
    crypto = Crypto()


    _encrypted_fields = ['name', 'phone', 'email', 'adress', 'country', 'nationality']

    @api.constrains('proofs')
    def _check_proofs(self):
        """
        Vérifie que les preuves jointes sont au format pdf.

        Si un enregistrement est créé sans pièce jointe, on s'en fiche.
        Si un enregistrement est créé avec des pièces jointes qui ne sont pas
        des pdf, on lève une erreur.
        """
        for record in self:
            if not record.proofs:
                # This can happen if you remove the last attachment.
                return
            for proof in record.proofs:
                if not proof.mimetype:
                    # This can happen if the mimetype is not set.
                    continue
                if proof.mimetype not in ('application/pdf'):
                    raise ValidationError(
                        "Les règlements de l'agence doivent être en pdf")
    
    """ @api.model
    def action_check_KEK(self):
        crypto = self.crypto

        if crypto.get_keyset():
            raise ValidationError(_("Une clé KEK existe déjà"))

        crypto.create_keyset()

        return True """
    @api.constrains('email')
    def _check_email(self):
        """Vérifie que l'email est valide."""
        email_regex = r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"
        for record in self:
            if record.email and not re.match(email_regex, record.email):
                raise ValidationError("L'adresse email n'est pas valide.")

    """ @api.constrains('phone')
    def _check_phone(self):
        Vérifie que le numéro de telephone est valide
        phone_regex = r"^\+\d{1,29}$"
        for record in self:
            if record.phone and not re.match(phone_regex, record.phone):
                raise ValidationError("Le numéro de téléphone n'est pas valide" ) """


    def _encrypt_fields(self, vals, reference):
        """Chiffre les champs définis dans _encrypted_fields."""
        crypto = self.crypto
        for field in self._encrypted_fields:
            if field in vals and vals[field]:
                vals[field] = crypto.encrypt_data(vals[field], reference)
        return vals

    def _decrypt_fields(self, records):
        """Déchiffre les champs définis dans _encrypted_fields pour chaque enregistrement."""
        crypto = self.crypto
        for record in records:
            for field in self._encrypted_fields:
                reference = self.env['insurance.security.clients'].browse(record['id']).reference
                if reference:
                    # Parcours des enregistrements pour déchiffrer les champs
                    if record[field]:
                        record[field] = crypto.decrypt_data(record[field], reference)
                else:
                    continue
        return records

    @api.model
    def create(self, vals):
        """
        Crée un nouvel enregistrement de client.

        :param dict vals: dictionnaire de valeurs à créer
        :return: l'enregistrement créé
        :rtype: odoo.models.Model
        """
        
        # créer clé Vault
        try:
            print(vals, 'vals')

            crypto = self.crypto

            # Générer tweak
            logical_id = crypto.generate_tweak()
            vals['reference'] = logical_id
             # chiffrer
            vals = self._encrypt_fields(vals, logical_id)
            return super().create(vals)
        except Exception as e:
            print("Aucune clé n'est pas trouvée, on utilise les valeurs originales : ", e)
            return super().create(vals)


    @api.model
    def export_data(self, fields_to_export):
        """
        Surcharge de la méthode d'exportation pour déchiffrer les champs avant l'exportation.

        :param list fields_to_export: list of fields
        :returns: dictionary with a *datas* matrix
        :rtype: dict
        """
        data = super().export_data(fields_to_export)

        try:

            # On déchiffre les champs si l'utilisateur a les droits pour cela
            if self.env.user.has_group('base.group_system'):
                crypto = self.crypto

                # Parcourir les enregistrements pour déchiffrer les champs
                for idx, record in enumerate(self):
                    reference = record.reference

                    # Parcourir les champs à déchiffrer
                    for i, field in enumerate(fields_to_export):
                        if field in self._encrypted_fields:
                            data['datas'][idx][i] = crypto.decrypt_data(
                                data['datas'][idx][i],
                                reference
                            )
            return data
        except Exception as e:
            print("Aucune clé n'est pas trouvée, on utilise les valeurs originales : ", e)
            return data

    def write(self, vals):
        """
        Surcharge de la méthode write pour chiffrer les champs avant la mise à jour.

        :param dict vals: dictionnaire de valeurs à mettre à jour
        :return: booléen indiquant si l'opération a réussi
        :rtype: bool
        """
        try : 

            crypto = self.crypto

            # Parcourir les enregistrements pour les mettre à jour
            for record in self:
                reference = record.reference

                if reference:
                    # Chiffrement des champs en utilisant la clé Vault
                    encrypted_vals = self._encrypt_fields(vals.copy(), reference)
                else:
                    # Aucune clé n'est pas trouvée, on utilise les valeurs originales
                    encrypted_vals = vals

                # Appel de la méthode write parent pour mettre à jour l'enregistrement
                super(InsuranceClients, record).write(encrypted_vals)

        except Exception as e:
            print("Aucune clé n'est pas trouvée, on utilise les valeurs originales : ", e)
            super(InsuranceClients, self).write(vals)

    def read(self, fields=None, load='_classic_read'):
        # Appel de la méthode read parent pour récupérer les enregistrements
        """
        Appel de la méthode read parent pour récupérer les enregistrements.
        Si une clé est trouvée, on déchiffre les champs chiffrés avant de les rechiffrer
        avec la nouvelle clé.
        Sinon, on utilise les valeurs originales.
        """
        
        try:
            records = super(InsuranceClients, self).read(fields, load)
            self._decrypt_fields(records)
            return records
        except Exception as e:
            print("clé non trouvée. On utilise les valeurs originales :", e)
            return super(InsuranceClients, self).read(fields, load)
    
    """A revoir complètement def search(self, domain, offset=0, limit=None, order=None, count=False):
        crypto = self.crypto    
        for field in self._encrypted_fields:
            print(field,'field')
            if field in domain and domain[field]:
                print(domain[field],'domain[field]')
                domain[field] = crypto.decrypt_data(domain[field], self.reference)
        return super().search(domain, offset, limit, order, count)"""

    def copy(self, default=None):
        # A controler
        """
        Copie l'enregistrement courant avec une nouvelle clé.
        
        :param dict default: dictionnaire contenant les valeurs par défaut pour la copie.
        :return: l'enregistrement copié.
        :rtype: InsuranceClients
        """

        default = dict(default or {})

        try:

            crypto = self.crypto

            # nouvelle référence
            new_ref = crypto.generate_tweak()
            default['reference'] = new_ref

            # déchiffrer puis rechiffrer avec nouvelle clé
            for field in self._encrypted_fields:
                if getattr(self, field):
                    decrypted = crypto.decrypt_data(getattr(self, field), self.reference)
                    default[field] = decrypted

            return super().copy(default)

        except Exception as e:
            print("Aucune clé n'est pas trouvée, on utilise les valeurs originales : ", e)
            return super().copy(default)
