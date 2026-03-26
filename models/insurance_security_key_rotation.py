from odoo import models, api
from ..utils.cryptofpe import Crypto

class KeyRotation(models.Model):
    _name = "insurance.key.rotation"
    _description = "Key Rotation Service"

    @api.model
    def action_generate_missing_key(self):
        crypto = Crypto()

        keyset = crypto.get_keyset()

        if not keyset:
            crypto.create_keyset()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Succès',
                'message': 'Clés générées pour les clients',
                'type': 'success',
            }
        }

            

    @api.model
    def rotate_keys(self):
        """
        Rotate the keys of the insurance security module.

        This function is used to rotate the keys that are used to encrypt the data in the insurance security module.
        It is called automatically by the system when the keys need to be rotated.

        """
        from ..utils.cryptocache import KeyCache

        KeyCache._cache = {}
        KeyCache._last_refresh = 0

        print("🔁 Rotation des clés effectuée")