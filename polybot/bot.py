import telebot
from loguru import logger
import os
import time
from telebot.types import InputFile
from polybot.img_proc import Img


class Bot:

    def __init__(self, token, telegram_chat_url):
        # create a new instance of the TeleBot class.
        # all communication with Telegram servers are done using self.telegram_bot_client
        self.telegram_bot_client = telebot.TeleBot(token)

        # remove any existing webhooks configured in Telegram servers
        self.telegram_bot_client.remove_webhook()
        time.sleep(0.5)

        # set the webhook URL
        self.telegram_bot_client.set_webhook(url=f'{telegram_chat_url}/{token}/', timeout=60)

        logger.info(f'Telegram Bot information\n\n{self.telegram_bot_client.get_me()}')

    def send_text(self, chat_id, text):
        self.telegram_bot_client.send_message(chat_id, text)

    def send_text_with_quote(self, chat_id, text, quoted_msg_id):
        self.telegram_bot_client.send_message(chat_id, text, reply_to_message_id=quoted_msg_id)

    def is_current_msg_photo(self, msg):
        return 'photo' in msg

    def download_user_photo(self, msg):
        """
        Downloads the photos that sent to the Bot to `photos` directory (should be existed)
        :return:
        """
        if not self.is_current_msg_photo(msg):
            raise RuntimeError(f'Message content of type \'photo\' expected')

        file_info = self.telegram_bot_client.get_file(msg['photo'][-1]['file_id'])
        data = self.telegram_bot_client.download_file(file_info.file_path)
        folder_name = file_info.file_path.split('/')[0]

        if not os.path.exists(folder_name):
            os.makedirs(folder_name)

        with open(file_info.file_path, 'wb') as photo:
            photo.write(data)

        return file_info.file_path

    def send_photo(self, chat_id, img_path):
        if not os.path.exists(img_path):
            raise RuntimeError("Image path doesn't exist")

        self.telegram_bot_client.send_photo(
            chat_id,
            InputFile(img_path)
        )

    def handle_message(self, msg):
        """Bot Main message handler"""
        logger.info(f'Incoming message: {msg}')
        self.send_text(msg['chat']['id'], f'Your original message: {msg["text"]}')


class QuoteBot(Bot):
    def handle_message(self, msg):
        logger.info(f'Incoming message: {msg}')

        if msg["text"] != 'Please don\'t quote me':
            self.send_text_with_quote(msg['chat']['id'], msg["text"], quoted_msg_id=msg["message_id"])


class ImageProcessingBot(Bot):
    def __init__(self, token, telegram_chat_url):
        super().__init__(token, telegram_chat_url)
        self.media_group = None
        self.filter = None
        self.filters_list = ["Blur", "Contour", "Rotate", "Segment", "Salt and pepper", "Concat", "Segment"]
        self.previous_pic = None

    @staticmethod
    def _apply_filter(img, filter):
        if filter == "Blur":
            img.blur()
        elif filter == "Contour":
            img.contour()
        elif filter == "Rotate":
            img.rotate()
        elif filter == "Segment":
            img.segment()
        elif filter == "Salt and pepper":
            img.salt_n_pepper()
        elif filter == "Segment":
            img.segment()

    def handle_message(self, msg):
        logger.info(f'Incoming message: {msg}')
        if self.media_group is None:
            self.media_group = msg.get("media_group_id")
        elif self.media_group != msg.get("media_group_id"):
            self.media_group = msg.get("media_group_id")
            self.filter = None

        if self.filter is None or msg.get("media_group_id") is None:
            if msg.get("caption"):
                self.filter = msg.get("caption")
            else:
                self.send_text(
                    msg['chat']['id'],
                    f"You have to provide a picture and one of the following filters: {self.filters_list}"
                )
                return None

        if self.filter == "Concat":
            if msg.get("media_group_id"):
                if msg.get("caption"):
                    photo_path = self.download_user_photo(msg)
                    process_photo = Img(photo_path)
                    self.previous_pic = process_photo
                else:
                    photo_path = self.download_user_photo(msg)
                    process_photo = Img(photo_path)
                    process_photo.concat(self.previous_pic)
                    processed_pic = process_photo.save_img()
                    self.send_photo(msg['chat']['id'], processed_pic)

        elif msg.get("media_group_id") is None:
            if self.filter in self.filters_list:
                try:
                    photo_path = self.download_user_photo(msg)
                    process_photo = Img(photo_path)
                    self._apply_filter(process_photo, self.filter)
                    self.filter = None
                    processed_pic = process_photo.save_img()
                    self.send_photo(msg['chat']['id'], processed_pic)
                except Exception:
                    self.send_text(
                        msg['chat']['id'],
                        f"An error occurred. You have to provide a picture and one of the following filters: {self.filters_list}"
                    )
            else:
                self.send_text(
                    msg['chat']['id'],
                    f"An error occurred. You have to provide a picture and one of the following filters: {self.filters_list}"
                )
                self.filter = None
        else:
            if self.filter in self.filters_list:
                try:
                    photo_path = self.download_user_photo(msg)
                    process_photo = Img(photo_path)
                    self._apply_filter(process_photo, self.filter)
                    processed_pic = process_photo.save_img()
                    self.send_photo(msg['chat']['id'], processed_pic)
                except Exception:
                    self.send_text(
                        msg['chat']['id'],
                        f"An error occurred. ou have to provide a picture and one of the following filters: {self.filters_list}"
                    )
            else:
                self.send_text(
                    msg['chat']['id'],
                    f"An error occurred. ou have to provide a picture and one of the following filters: {self.filters_list}"
                )
                self.filter = None
