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
        self.continuous_command = None
        self.previous_pic = None

    def handle_message(self, msg):
        logger.info(f'Incoming message: {msg}')
        if msg.get("caption"):
            photo_path = self.download_user_photo(msg)
            process_photo = Img(photo_path)
            known_filter = True

            if self.media_group is not None and msg.get("media_group_id"):
                self.media_group = msg.get("media_group_id")
                self.continuous_command = None

            if self.continuous_command is not None and msg.get("caption") is None:
                apply_filter = self.continuous_command
            else:
                apply_filter = msg.get("caption")
                self.continuous_command = None

            if apply_filter == "blur":
                process_photo.blur()
                self.continuous_command = "blur"
            elif apply_filter == "contour":
                process_photo.contour()
                self.continuous_command = "contour"
            elif apply_filter == "rotate":
                process_photo.rotate()
                self.continuous_command = "rotate"
            elif apply_filter == "salt_n_pepper":
                process_photo.salt_n_pepper()
                self.continuous_command = "salt_n_pepper"
            elif apply_filter == "concat":
                if self.media_group:
                    process_photo.concat(self.previous_pic)
                    self.previous_pic = None
                else:
                    self.previous_pic = process_photo
                self.continuous_command = "concat"
            elif apply_filter == "segment":
                process_photo.segment()
                self.continuous_command = "segment"
            else:
                self.send_text(msg['chat']['id'], "I don't know this filter, you may meant something else?")
                known_filter = False

            if known_filter and not self.previous_pic:
                processed_pic = process_photo.save_img()
                self.send_photo(msg['chat']['id'], processed_pic)
            print(msg)

        #     print(msg["caption"])
        # for i in msg:
        #     print(f"TEST: {i}")
