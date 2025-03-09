import sqlite3
from datetime import datetime
from config import DATABASE 
import os
import cv2
import numpy as np
from logic import *
from math import sqrt, ceil, floor

class DatabaseManager:
    def __init__(self, database):
        self.database = database

    def create_tables(self):
        conn = sqlite3.connect(self.database)
        with conn:
            conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                user_name TEXT
            )
        ''')

            conn.execute('''
            CREATE TABLE IF NOT EXISTS prizes (
                prize_id INTEGER PRIMARY KEY,
                image TEXT,
                used INTEGER DEFAULT 0
            )
        ''')

            conn.execute('''
            CREATE TABLE IF NOT EXISTS winners (
                user_id INTEGER,
                prize_id INTEGER,
                win_time TEXT,
                FOREIGN KEY(user_id) REFERENCES users(user_id),
                FOREIGN KEY(prize_id) REFERENCES prizes(prize_id)
            )
        ''')

            conn.commit()

    def add_user(self, user_id, user_name):
        conn = sqlite3.connect(self.database)
        with conn:
            conn.execute('INSERT INTO users VALUES (?, ?)', (user_id, user_name))
            conn.commit()

    def add_prize(self, data):
        conn = sqlite3.connect(self.database)
        with conn:
            conn.executemany('''INSERT INTO prizes (image) VALUES (?)''', data)
            conn.commit()

    def add_winner(self, user_id, prize_id):
        win_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor() 
            cur.execute("SELECT * FROM winners WHERE user_id = ? AND prize_id = ?", (user_id, prize_id))
            if cur.fetchall():
                return 0
            else:
                conn.execute('''INSERT INTO winners (user_id, prize_id, win_time) VALUES (?, ?, ?)''', (user_id, prize_id, win_time))
                conn.commit()
                return 1

  
    def mark_prize_used(self, prize_id):
        conn = sqlite3.connect(self.database)
        with conn:
            conn.execute('''UPDATE prizes SET used = 1 WHERE prize_id = ?''', (prize_id,))
            conn.commit()

    def get_users(self):
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            cur.execute('SELECT * FROM users')
            return [x[0] for x in cur.fetchall()] 
        
    def get_prize_img(self, prize_id):
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            cur.execute('SELECT image FROM prizes WHERE prize_id = ?', (prize_id, ))
            return cur.fetchall()[0][0]
            
    def get_random_prize(self):
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            cur.execute('SELECT * FROM prizes WHERE used = 0 ORDER BY RANDOM()')
            return cur.fetchall()[0]

    def get_winners_count(self, prize_id):
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            cur.execute('SELECT COUNT(*) FROM winners WHERE prize_id = ?', (prize_id, ))
            return cur.fetchall()[0][0]

    def get_rating(self):
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            cur.execute('''
            SELECT users.user_name, COUNT(winners.prize_id) as count_prize 
            FROM winners
            INNER JOIN users ON users.user_id = winners.user_id
            GROUP BY winners.users_id
            ORDER BY count_prize
            LIMIT 10
            ''')

    # Kullanıcının kazandığı ödülleri getirme
    def get_winners_img(self, user_id):
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            cur.execute('''
                SELECT prizes.image FROM winners 
                INNER JOIN prizes ON winners.prize_id = prizes.prize_id
                WHERE winners.user_id = ?
            ''', (user_id,))
            return [x[0] for x in cur.fetchall()]

    def create_collage(self, user_id):
        # Kullanıcının kazandığı resimleri al
        won_prizes = self.get_winners_img(user_id)

        # 'hidden_img' klasöründeki toplanmamış (gizlenmiş) resimleri al
        hidden_images = os.listdir('hidden_img')

        # Toplanmamış resimleri veritabanında kontrol et ve onları listeye ekle
        hidden_image_paths = [
            f'hidden_img/{x}' for x in hidden_images
            if os.path.exists(f'hidden_img/{x}') and self.is_image_hidden(x)
        ]

        # Kazanılmış ve gizlenmiş tüm resimleri birleştir
        all_image_paths = [f'img/{x}' for x in won_prizes] + hidden_image_paths

        # Eğer hiç resim yoksa None dön
        if not all_image_paths:
            return None

        # Resimleri okuyalım
        images = [cv2.imread(path) for path in all_image_paths]

        num_images = len(images)
        num_cols = floor(sqrt(num_images))  
        num_rows = ceil(num_images / num_cols)

        # Kolajın boyutunu belirleme
        img_h, img_w, _ = images[0].shape
        collage = np.zeros((num_rows * img_h, num_cols * img_w, 3), dtype=np.uint8)

        for i, img in enumerate(images):
            row = i // num_cols
            col = i % num_cols
            collage[row * img_h:(row + 1) * img_h, col * img_w:(col + 1) * img_w, :] = img

        # Kolajı kaydet
        collage_path = f'collages/collage_{user_id}.jpg'
        cv2.imwrite(collage_path, collage)
        return collage_path

    def is_image_hidden(self, img_name):
        # Veritabanındaki gizlenmiş resimleri kontrol et
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            cur.execute('SELECT * FROM winners WHERE prize_id = (SELECT prize_id FROM prizes WHERE image = ?)', (img_name,))
            return cur.fetchone() is None
                        
def hide_img(img_name):
    image = cv2.imread(f'img/{img_name}')
    blurred_image = cv2.GaussianBlur(image, (15, 15), 0)
    pixelated_image = cv2.resize(blurred_image, (30, 30), interpolation=cv2.INTER_NEAREST)
    pixelated_image = cv2.resize(pixelated_image, (image.shape[1], image.shape[0]), interpolation=cv2.INTER_NEAREST)
    cv2.imwrite(f'hidden_img/{img_name}', pixelated_image)

if __name__ == '__main__':
    manager = DatabaseManager(DATABASE)
    manager.create_tables()
    prizes_img = os.listdir('img')
    data = [(x,) for x in prizes_img]
    manager.add_prize(data)