from odoo import fields, models, api, _
from ..utils.cryptofpe import Crypto
from odoo.exceptions import ValidationError

import logging
import re

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

    crypto = Crypto()

    # Initialisation du Json
    keyset_key = fields.Json()


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

    def _encrypt_value(self, value, keyset_key):
        """Chiffre une valeur si elle n'est pas vide."""
        try:
            return self.crypto.encrypt_data(value, keyset_key) if value else value
        except Exception as e:
            _logger.error(f"Erreur lors du chiffrement de la valeur: {e}")
            return value

    def _decrypt_value(self, value, keyset_key):
        """Déchiffre une valeur si elle n'est pas vide."""
        try:
            return self.crypto.decrypt_data(value, keyset_key) if value else value
        except Exception as e:
            _logger.error(f"Erreur lors du déchiffrement de la valeur: {e}")
            return value

    def _encrypt_fields(self, vals, keyset_key):
        """Chiffre les champs définis dans _encrypted_fields."""
        for field in self._encrypted_fields:
            print(field,'field')
            if field in vals and vals[field]:
                print(vals[field],'vals[field]')
                vals[field] = self._encrypt_value(vals[field], keyset_key)
        return vals

    def _decrypt_fields(self, records):
        """Déchiffre les champs définis dans _encrypted_fields pour chaque enregistrement."""
        for record in records:
            json = self.env['insurance.security.clients'].browse(record['id']).keyset_key
            for field in self._encrypted_fields:
                print(field, 'field')
                # Parcours des enregistrements pour déchiffrer les champs
                if record[field]:
                    record[field] = self._decrypt_value(record[field], json)
        return records

    @api.model
    def create(self, vals):
        print(vals, 'vals')
        
        """ # Génération d'un nouveau keyset et mise à jour de vals
        if not vals.get('keyset_key'):
            vals['keyset_key'] = self.crypto.create_keyset()
        
        # Chiffrement des champs en utilisant le keyset_key
        if 'keyset_key' in vals:
            vals = self._encrypt_fields(vals, vals['keyset_key'])
        
            # Appel à la méthode create parent
            return super(InsuranceClients, self).create(vals) """

        return super(InsuranceClients, self).create(vals)


    @api.model
    def export_data(self, fields_to_export):
        """
        Surcharge de la méthode d'exportation pour déchiffrer les champs avant l'exportation.
        """
        # Appel de la méthode d'exportation d'origine pour obtenir les données à exporter
        data = super(InsuranceClients, self).export_data(fields_to_export)

        # Récupérer les indices des champs à déchiffrer
        encrypted_field_indices = [i for i, field in enumerate(fields_to_export) if field in self._encrypted_fields]

        records = self.env['insurance.security.clients'].search([])
        keyset_keys = [record.keyset_key for record in records]
        i = 0

        # Parcourir les enregistrements pour déchiffrer les champs cryptés
        for row in data['datas']:
            json = keyset_keys[i]
            i += 1
            for index in encrypted_field_indices:
                if row[index]:
                    row[index] = self._decrypt_value(row[index], json)
        return data

    def write(self, vals):
        vals = self._encrypt_fields(vals, vals['keyset_key'])
        return super(InsuranceClients, self).write(vals)

    def read(self, fields=None, load='_classic_read'):
        # Appel de la méthode read parent pour récupérer les enregistrements
        records = super(InsuranceClients, self).read(fields, load)
        #self._decrypt_fields(records)
        return records
