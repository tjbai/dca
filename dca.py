import os, sys, logging, argparse
from datetime import datetime
from coinbase.rest import RESTClient
from logging.handlers import RotatingFileHandler
from telegram import Bot
from functools import partial

os.makedirs('logs', exist_ok=True)
cur_day = datetime.now().strftime('%Y-%m-%d')

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
for handler in [RotatingFileHandler(filename=f'logs/{cur_day}.log', maxBytes=1024*1024, backupCount=1), logging.StreamHandler(sys.stdout)]:
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)

async def log_and_notify(bot, chat_id, msg, is_error=False):
    logger.error(msg) if is_error else logger.info(msg)
    await bot.send_message(chat_id=chat_id, text=msg)

def get_market_price(client, prod_id):
    return client.get_product(prod_id).price

def create_buy_order(client, prod_id, amt_usd):
    return client.market_order_buy(client_order_id=f'{prod_id}-{cur_day}', product_id=prod_id, quote_size=amt_usd)
    # return client.limit_order_gtc_buy(client_order_id=f'{prod_id}-{cur_day}', product_id=prod_id, base_size=str(1), limit_price=str(0))

def parse_args():
    parser = argparse.ArgumentParser()

    # order params
    parser.add_argument('--quote-size')
    parser.add_argument('--prod-id', default='BTC-USD')

    # cb stuff
    parser.add_argument('--cb-key-file')
    parser.add_argument('--cb-api-key')
    parser.add_argument('--cb-api-secret')

    # tg stuff
    parser.add_argument('--tg-bot-token')
    parser.add_argument('--tg-chat-id')

    return parser.parse_args()

async def main():
    args = parse_args()
    tg_bot = Bot(args.tg_bot_token)
    cb_client = RESTClient(key_file=args.cb_key_file) if args.cb_key_file else RESTClient(args.cb_api_key, args.cb_api_secret)
    log = partial(log_and_notify, tg_bot, args.tg_chat_id)

    try:
        price = get_market_price(cb_client, args.prod_id)
        await log(f'market price for {args.prod_id} is {price}')
    except Exception:
        await log(f'could not fetch market price for {args.prod_id}', True)

    try:
        resp = create_buy_order(cb_client, 'BTC-USD', str(args.quote_size))
        if not resp.success: raise Exception(resp.response)
        await log(f'successfully created ${args.quote_size} order for {args.prod_id}')
    except Exception as e:
        await log(f'failed to create order... {e}', True)

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
