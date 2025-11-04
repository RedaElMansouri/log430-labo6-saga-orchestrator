"""
Handler: decrease stock
SPDX - License - Identifier: LGPL - 3.0 - or -later
Auteurs : Gabriel C. Ullmann, Fabio Petrillo, 2025
"""
import config
import requests
from logger import Logger
from handlers.handler import Handler
from order_saga_state import OrderSagaState

class DecreaseStockHandler(Handler):
    """ Handle the stock check-out of a given list of products and quantities. Trigger rollback of previous steps in case of failure. """

    def __init__(self, order_item_data):
        """ Constructor method """
        self.order_item_data = order_item_data
        super().__init__()

    def run(self):
        """Call StoreManager to check out from stock"""
        try:
            # !Warning!: Si exécution du code dans Docker, utilisez hostname du API Gateway et pas localhost
            response = requests.post(
                f"{config.API_GATEWAY_URL}/store-manager-api/stocks",
                json={
                    "items": self.order_item_data,
                    "operation": "-"
                },
                headers={'Content-Type': 'application/json'}
            )

            if response.ok:
                self.logger.debug("La sortie des articles du stock a réussi")
                return OrderSagaState.CREATING_PAYMENT
            else:
                error_text = None
                try:
                    error_text = response.json()
                except Exception:
                    error_text = response.text
                self.logger.error(f"Erreur {response.status_code} lors de la sortie de stock : {error_text}")
                return OrderSagaState.CANCELLING_ORDER

        except Exception as e:
            self.logger.error("La sortie des articles du stock a échoué : " + str(e))
            return OrderSagaState.CANCELLING_ORDER
        
    def rollback(self):
        """ Call StoreManager to revert stock check out (in other words, check-in the previously checked-out product and quantity) """
        try:
            # !Warning!: Si exécution du code dans Docker, utilisez hostname du API Gateway et pas localhost
            response = requests.post(
                f"{config.API_GATEWAY_URL}/store-manager-api/stocks",
                json={
                    "items": self.order_item_data,
                    "operation": "+"
                },
                headers={'Content-Type': 'application/json'}
            )

            if response.ok:
                self.logger.debug("L'entrée des articles dans le stock a réussi")
            else:
                error_text = None
                try:
                    error_text = response.json()
                except Exception:
                    error_text = response.text
                self.logger.error(f"Erreur {response.status_code} lors de l'entrée de stock (rollback) : {error_text}")
        except Exception as e:
            self.logger.error("L'entrée des articles dans le stock a échoué (rollback) : " + str(e))

        return OrderSagaState.CANCELLING_ORDER