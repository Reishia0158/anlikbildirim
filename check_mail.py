import os
import imaplib
import email
from email.header import decode_header
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
import sys

# Environment variables
IMAP_HOST = os.getenv('IMAP_HOST', 'imap.gmail.com')
IMAP_PORT = int(os.getenv('IMAP_PORT', '993'))
IMAP_USER = os.getenv('IMAP_USER')
IMAP_PASS = os.getenv('IMAP_PASS')
TOPIC_URL = os.getenv('TOPIC_URL')  # Örn: https://ntfy.sh/your-topic-name

# Dosya yolu
LAST_UID_FILE = 'last_uid.txt'

def get_last_uid():
    """Son kaydedilmiş UID'yi dosyadan okur."""
    try:
        if os.path.exists(LAST_UID_FILE):
            with open(LAST_UID_FILE, 'r') as f:
                return int(f.read().strip())
        return None
    except (ValueError, IOError) as e:
        print(f"⚠️ Last UID okuma hatası: {e}")
        return None

def save_last_uid(uid):
    """Son UID'yi dosyaya kaydeder."""
    try:
        with open(LAST_UID_FILE, 'w') as f:
            f.write(str(uid))
        print(f"✅ Last UID kaydedildi: {uid}")
    except IOError as e:
        print(f"❌ Last UID kaydetme hatası: {e}")

def send_ntfy_notification(message):
    """ntfy.sh'e bildirim gönderir."""
    if not TOPIC_URL:
        print("⚠️ TOPIC_URL tanımlı değil, bildirim gönderilemiyor")
        return False
    
    try:
        # POST isteği oluştur
        req = Request(TOPIC_URL, data=message.encode('utf-8'), method='POST')
        req.add_header('Content-Type', 'text/plain')
        
        # İsteği gönder
        with urlopen(req, timeout=10) as response:
            if response.status == 200:
                print(f"✅ Bildirim gönderildi: {message}")
                return True
            else:
                print(f"⚠️ Bildirim gönderme hatası: HTTP {response.status}")
                return False
    except (URLError, HTTPError) as e:
        print(f"❌ ntfy bağlantı hatası: {e}")
        return False
    except Exception as e:
        print(f"❌ Bildirim gönderme hatası: {e}")
        return False

def check_new_mails():
    """IMAP üzerinden yeni mailleri kontrol eder."""
    if not IMAP_USER or not IMAP_PASS:
        print("❌ IMAP_USER veya IMAP_PASS tanımlı değil!")
        return False
    
    try:
        # IMAP bağlantısı kur
        print(f"🔌 IMAP bağlantısı kuruluyor: {IMAP_HOST}:{IMAP_PORT}")
        mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
        
        # Giriş yap
        print(f"🔐 Giriş yapılıyor: {IMAP_USER}")
        mail.login(IMAP_USER, IMAP_PASS)
        print("✅ Giriş başarılı")
        
        # INBOX'u seç
        mail.select('INBOX')
        
        # Tüm mail UID'lerini al (en yeni önce)
        status, messages = mail.uid('search', None, 'ALL')
        if status != 'OK':
            print("❌ Mail arama hatası")
            mail.logout()
            return False
        
        # UID listesini al
        uid_list = messages[0].split()
        if not uid_list:
            print("ℹ️ INBOX'ta mail yok")
            mail.logout()
            return False
        
        # En yeni UID'yi al (son eleman)
        latest_uid = int(uid_list[-1])
        print(f"📧 En yeni mail UID: {latest_uid}")
        
        # Son kaydedilmiş UID'yi al
        last_uid = get_last_uid()
        
        if last_uid is None:
            # İlk çalıştırma - sadece UID'yi kaydet, bildirim gönderme
            print("ℹ️ İlk çalıştırma - UID kaydediliyor, bildirim gönderilmiyor")
            save_last_uid(latest_uid)
            mail.logout()
            return True
        
        print(f"📋 Son kaydedilmiş UID: {last_uid}")
        
        # Yeni mail var mı?
        if latest_uid > last_uid:
            new_count = latest_uid - last_uid
            print(f"🎉 Yeni mail bulundu! ({new_count} adet)")
            
            # Bildirim gönder
            notification_message = f"Yeni mailiniz var! ({new_count} yeni mesaj)"
            send_ntfy_notification(notification_message)
            
            # Yeni UID'yi kaydet
            save_last_uid(latest_uid)
        else:
            print("ℹ️ Yeni mail yok")
        
        # Bağlantıyı kapat
        mail.logout()
        return True
        
    except imaplib.IMAP4.error as e:
        print(f"❌ IMAP hatası: {e}")
        return False
    except Exception as e:
        print(f"❌ Beklenmeyen hata: {e}")
        return False

def main():
    """Ana fonksiyon."""
    print("=" * 50)
    print("📬 Mail Kontrol Başlatılıyor...")
    print("=" * 50)
    
    try:
        success = check_new_mails()
        if success:
            print("✅ Mail kontrolü tamamlandı")
            sys.exit(0)
        else:
            print("⚠️ Mail kontrolü sırasında hata oluştu")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️ İşlem kullanıcı tarafından durduruldu")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Kritik hata: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
