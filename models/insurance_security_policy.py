from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta
from ..utils.cryptofpe import Crypto
import logging

_logger = logging.getLogger(__name__)

class InsurancePolicy(models.Model):
    _name = "insurance.security.policy"
    _description = "Polices d'assurance"

    name = fields.Char(string='Numéro de Police', required=True, copy=False, readonly=True, index=True, default=lambda self: _('New'))
    duration = fields.Integer(string='Temps d\'émission de la police (en mois)', copy=False, required=True)
    start_date = fields.Date(string='Date de Début', required=True)
    end_date = fields.Date(string='Date de Fin', required=True)
    currency_id = fields.Many2one("res.currency", string="Devise", required=True)
    prime = fields.Float(string='Prime de l\'assurance', copy=False, required=True)
    state = fields.Selection(
        [
            ('progress', 'En cours'), 
            ('confirmed', 'Confirmer'), 
            ('closed', 'Fermer')
        ],
        required=True, 
        default='progress')
    conditions = fields.Html("Conditions et Obligations", required=True)
    
    regulations = fields.Many2many(
        'ir.attachment', 
        string='Règlements de l\'agence', 
        help='Veuillez insérer les règlements de l\'agence ainsi que tous les autres documents conformément à sa police d\'assurance'
    )
   
    
    agent_id = fields.Many2one("insurance.security.agents", string = "Agents")
    agent_name = fields.Char( related='agent_id.name', string="Nom de l'agent", required=True, copy=False, readonly=True)
    agent_phone = fields.Char( related='agent_id.phone', string="Numéro de téléphone de l'agent", copy=False, readonly=True)
    agent_email = fields.Char( related='agent_id.email', string="Email", copy=False, readonly=True)
    
    client_id = fields.Many2one("insurance.security.clients", string = "Client ")
    client_name = fields.Char( related='client_id.name', string="Nom du client", copy=False, readonly=True)
    client_phone = fields.Char( related='client_id.phone', string="Numéro de téléphone du client", copy=False, readonly=True)
    client_email = fields.Char( related='client_id.email', string="Email", copy=False, readonly=True)

    # Initialisation de cryptofpe le code source pour le cryptage et le décryptage
    crypto = Crypto()

    reference = fields.Char(string="Key Reference")
    
    _encrypted_fields = [ 'name']
    _agent_fields = ['agent_name', 'agent_phone', 'agent_email']
    _client_fields = ['client_name', 'client_phone', 'client_email']

    @api.constrains('duration')
    def _check_duration(self):
        """ Vérifie que la durée n'est pas négatif. """
        for record in self:
            if record.duration < 0:
                raise ValidationError(
                    "Le temps n'est pas négatif")
    
    @api.constrains('prime')
    def _check_prime(self):
        """ Vérifie que la prime n'est pas négatif. """
        for record in self:
            if record.prime < 0 or record.prime == 0:
                raise ValidationError(
                    "La prime n'est pas négatif ou nulle")

    @api.constrains('regulations')
    def _check_proofs(self):
        """
        Vérifie que les preuves jointes sont au format pdf.

        Si un enregistrement est créé sans pièce jointe, on s'en fiche.
        Si un enregistrement est créé avec des pièces jointes qui ne sont pas
        des pdf, on lève une erreur.
        """
        for record in self:
            if not record.regulations:
                # This can happen if you remove the last attachment.
                return
            for proof in record.regulations:
                if not proof.mimetype:
                    # This can happen if the mimetype is not set.
                    continue
                if proof.mimetype not in ('application/pdf'):
                    raise ValidationError(
                        "Les règlements de l'agence doivent être en pdf")

    @api.onchange("duration")
    def _onchange_date(self):
        """
        When the duration of insurance is changed, this method is triggered.
        If the duration is given, the start_date and end_date are updated.
        Otherwise, the start_date and end_date are set to the current date.
        """
        if self.duration:
            self.start_date = fields.Datetime.today()
            self.end_date = fields.Datetime.today() + relativedelta(months=self.duration)
        else:
            self.start_date = fields.Datetime.today()
            self.end_date = fields.Datetime.today()
    

    def confirm_insurance(self):
        """
        Confirme la police d'assurance.
        
        Si la prime est supérieur à zero, le status de la police est mis à jour en "confirmed".
        Sinon, une erreur est levée.
        """
        if self.prime > 0:
            self.state = 'confirmed'
        else:
            raise UserError(_("La prime doit être supérieur à zero"))

    def action_send_email(self):
        """
        Send the email to the client after confirming the policy.
        """
        
        mail_template = self.env.ref('insurance_security.insurance_security_policy_email_template')
        mail_template.send_mail(self.id, force_send=True)

   
    def _encrypt_fields(self, vals, reference):
        """Chiffre les champs définis dans _encrypted_fields."""
        crypto = self.crypto
        for field in self._encrypted_fields:
            print(field,'field')
            if field in vals and vals[field]:
                print(vals[field],'vals[field]')
                vals[field] = crypto.encrypt_data(vals[field], reference)
        return vals

    def _decrypt_fields(self, records):
        """Déchiffre les champs définis dans _encrypted_fields pour chaque enregistrement."""
        crypto = self.crypto
        for record in records:
            print(record, 'record in _decrypt_fields method of InsurancePolicy')
            client_id = record.get('client_id')
            if client_id:
                client = self.env['insurance.security.clients'].browse(client_id[0])
                print(client, 'client')
                reference = self.reference
                for field in self._encrypted_fields:
                    # Parcours des enregistrements pour déchiffrer les champs
                    if record[field]:
                        record[field] = crypto.decrypt_data(record[field], reference)
                reference_client = client.reference
                for field in self._client_fields:
                    # Parcours des enregistrements pour déchiffrer les champs
                    if record[field]:
                        record[field] = crypto.decrypt_data(record[field], reference_client)
            agent_id = record.get('agent_id')
            if agent_id:
                agent = self.env['insurance.security.agents'].browse(agent_id[0])
                reference_agent = agent.reference
                for field in self._agent_fields:
                    # Parcours des enregistrements pour déchiffrer les champs
                    if record[field]:
                        record[field] = crypto.decrypt_data(record[field], reference_agent)
        return records



    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('policy.details') or 'New'
        
        # créer clé Vault
        try:
            crypto = self.crypto

            # Générer tweak
            logical_id = crypto.generate_tweak()
            vals['reference'] = logical_id
            # chiffrer
            vals = self._encrypt_fields(vals, logical_id)

        except Exception as e:
            print("Aucune clé n'est pas trouvée, on utilise les valeurs originales : ", e)

        
        #stocker référence (PAS la clé !)
        

        print(vals, ": vals après enceyp")

        return super().create(vals)
    
    
    def write(self, vals):
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
            super(InsurancePolicy, record).write(encrypted_vals)

        return True

    def read(self, fields=None, load='_classic_read'):
        try:
            records = super(InsurancePolicy, self).read(fields, load)
            self._decrypt_fields(records)
            return records
        except:
            print("clé non trouvée")
            return super(InsurancePolicy, self).read(fields, load)

    @api.model
    def export_data(self, fields_to_export):
        """
        Surcharge de la méthode d'exportation pour déchiffrer les champs avant l'exportation.
        """
        # Appel de la méthode d'exportation d'origine pour obtenir les données à exporter
        data = super(InsurancePolicy, self).export_data(fields_to_export)

        # Récupérer les indices des champs à déchiffrer
        encrypted_field_indices = [i for i, field in enumerate(fields_to_export) if field in self._encrypted_fields]
        agents_field_indices = [i for i, field in enumerate(fields_to_export) if field in self._agent_fields]
        clients_field_indices = [i for i, field in enumerate(fields_to_export) if field in self._client_fields]

        records = self.env['insurance.security.policy'].search([])
        clients_reference = [record.client_id.keyset_key for record in records]
        agents_reference = [record.agent_id.keyset_key for record in records]
        policy_reference = [record.reference for record in records]
        i = 0

        # Parcourir les enregistrements pour déchiffrer les champs cryptés
        if self.env.user.has_group('base.group_system'):
            crypto = self.crypto
            for row in data['datas']:
                reference_clients = clients_reference[i]
                reference_agents = agents_reference[i]
                reference_policy = policy_reference[i]
                i += 1
                for index in encrypted_field_indices:
                    if row[index]:
                        row[index] = crypto.decrypt_data(row[index], reference_policy)
                for index in agents_field_indices:
                    if row[index]:
                        row[index] = crypto.decrypt_data(row[index], reference_agents)
                for index in clients_field_indices:
                    if row[index]:
                        row[index] = crypto.decrypt_data(row[index], reference_clients)

        return data

        

