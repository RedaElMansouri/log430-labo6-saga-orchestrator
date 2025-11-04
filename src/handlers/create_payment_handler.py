"""
Handler: create payment transaction
SPDX - License - Identifier: LGPL - 3.0 - or -later
Auteurs : Gabriel C. Ullmann, Fabio Petrillo, 2025
"""
import config
import requests
from logger import Logger
from handlers.handler import Handler
from order_saga_state import OrderSagaState

class CreatePaymentHandler(Handler):
    """ Handle the creation of a payment transaction for a given order. Trigger rollback of previous steps in case of failure. """

    def __init__(self, order_id, order_data):
        """ Constructor method """
        self.order_id = order_id
        self.order_data = order_data
        self.total_amount = 0
        super().__init__()

    def run(self):
        """Call payment microservice to generate payment transaction"""
        try:
            order_resp = requests.get(
                f"{config.API_GATEWAY_URL}/store-manager-api/orders/{self.order_id}",
                headers={'Content-Type': 'application/json'}
            )
            if not order_resp.ok:
                err = None
                try:
                    err = order_resp.json()
                except Exception:
                    err = order_resp.text
                self.logger.error(f"Erreur {order_resp.status_code} lors de la récupération de la commande {self.order_id}: {err}")
                return OrderSagaState.INCREASING_STOCK

            order_data = order_resp.json() or {}
            self.total_amount = order_data.get('total_amount', 0)

            payment_payload = {
                "order_id": self.order_id,
                "user_id": self.order_data.get("user_id"),
                "amount": self.total_amount
            }
            pay_resp = requests.post(
                f"{config.API_GATEWAY_URL}/payments-api/payments",
                json=payment_payload,
                headers={'Content-Type': 'application/json'}
            )
            if pay_resp.ok:
                self.logger.debug("La création d'une transaction de paiement a réussi")
                return OrderSagaState.COMPLETED
            else:
                err = None
                try:
                    err = pay_resp.json()
                except Exception:
                    err = pay_resp.text
                self.logger.error(f"Erreur {pay_resp.status_code} lors de la création du paiement : {err}")
                return OrderSagaState.INCREASING_STOCK

        except Exception as e:
            self.logger.error("La création d'une transaction de paiement a échoué : " + str(e))
            return OrderSagaState.INCREASING_STOCK
        
    def rollback(self):
        """Call payment microservice to delete payment transaction"""
        # ATTENTION: Nous pourrions utiliser cette méthode si nous avions des étapes supplémentaires, mais ce n'est pas le cas actuellement, elle restera donc INUTILISÉE.
        self.logger.debug("La suppression d'une transaction de paiement a réussi")
        return OrderSagaState.INCREASING_STOCK