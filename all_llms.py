from openai import OpenAI
import json
from typing import List, Dict, Tuple, Optional
import os 
from datetime import datetime

llm_api_key = os.getenv("LLM_API_KEY")
llm_name= os.getenv("LLM_MODEL_NAME")


client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=llm_api_key,
    default_headers={
        "HTTP-Referer": "http://localhost:5000",
        "X-Title": "Flight Booking Assistant"
    }
)

bugun = datetime.now()

gun = bugun.day
ay = bugun.month
yil = bugun.year


def send_message_to_flight_llm(message: str, history: List[Dict] = None) -> Tuple[str, List[Dict]]:
    """
    Uçuş asistanı özelinde LLM'e mesaj gönderen ve cevap dönen fonksiyon
    Args:
        message: Gönderilecek mesaj
        history: Önceki mesajların geçmişi
    Returns:
        response_content: LLM'den gelen cevap (formatted text)
        updated_history: Güncellenmiş mesaj geçmişi
    """
    if history is None:
        history = []
        
    system_prompt = f"""
    Sen bir uçuş asistanısın. Sadece uçak bileti bilgilerini alabilirsin. Dönüş mesajların her zaman Türkçe olmalı. 
    Onun dışında herhangi bir konuda yardımcı olamayacağını Türkçe ve kibar bir şekilde belirtmelisin.
    Şu anda tarih {gun} {ay} {yil}. 
    Ayrıca kullanıcı ufak tefek yazım hataları yapabilir, buna takılma.Çıkarabildiğin bilgiyi çıkar. 
    Eğer kullanıcı daha önceden verdiği bir bilgiyi değiştirmek isterse ona izin ver ve sen de tuttuğun bilgiyi güncelle.    
    
    Kullanıcıdan gelen mesajı ve önceki mesajları analiz et. Üç türlü yanıt verebilirsin:

    1. Eğer tüm bilgiler tamamsa ama henüz onaylanmamışsa, şu formatta yanıt ver:
    ONAY: [nereden] [nereye] [tarih GG Ay YYYY]'te tek yön. Bu bilgiler doğru mu? Onaylıyorsanız belirtin, değilse hangi bilgileri değiştirmek istediğinizi belirtin.
    veya
    ONAY: [nereden] [nereye] [gidiş tarihi GG Ay YYYY]'te gidiş [dönüş tarihi GG Ay YYYY]'te dönüş. Bu bilgiler doğru mu? Onaylıyorsanız 'evet' yazın, değilse hangi bilgileri değiştirmek istediğinizi belirtin.

    2. Eğer eksik bilgi varsa, şu formatta yanıt ver:
    EKSİK: [eksik bilgilerin listesi]

    3. Eğer tüm bilgiler tamam ve onaylandıysa, şu formatta yanıt ver:
    TAMAM: [nereden] [nereye] [tarih GG Ay YYYY]'te tek yön
    veya
    TAMAM: [nereden] [nereye] [gidiş tarihi GG Ay YYYY]'te gidiş [dönüş tarihi GG Ay YYYY]'te dönüş
    
    Örnek yanıtlar:
    "ONAY: Ankaradan İstanbula 23 Mart 2025'te tek yön. Bu bilgiler doğru mu?"
    "EKSİK: gidiş tarihi, uçuşun tek yön mü gidiş-dönüş mü olduğu"
    "TAMAM: Ankaradan İstanbula 23 Mart 2025'te tek yön"

    Önemli kurallar:
    1. Önceki mesajlarda verilmiş bilgileri tekrar isteme
    2. Eksik bilgiler kısmına sadece henüz hiç belirtilmemiş bilgileri ekle
    3. Bir bilgi daha önce verildiyse onu kullan
    4. Tarihleri GG Ay YYYY formatında yaz (örnek: 23 Mart 2025)
    5. Eğer kullanıcı bilgileri onaylamazsa, değiştirmek istediği bilgileri sor
    6. Kullanıcı 'evet' derse veya onayladığını belirten bir mesaj yazarsa, TAMAM ile başlayan son hali dön
    """
    
    # ...existing code...
    
    if not history:
        history.append({"role": "system", "content": system_prompt})
    
    history.append({"role": "user", "content": message})
    
    response = client.chat.completions.create(
        model=llm_name,
        messages=history,
        temperature=0.2,
        response_format={"type": "json_object"}
    )
    
    response_content = response.choices[0].message.content
    history.append({"role": "assistant", "content": response_content})
    
    return response_content, history


def send_message_to_flight_search_llm(flight_details: str, history: List[Dict] = None) -> Tuple[str, List[Dict]]:
    """
    Uçuş arama asistanı LLM'i
    """
    if history is None:
        history = []
        
    system_prompt = """
        Sen bir uçuş arama asistanısın. Sana verilen uçuş detaylarını aşağıdaki formatta parse etmelisin:
        {
            "from": "şehir_kodu",
            "to": "şehir_kodu",
            "departure_date": "YYYY-AA-GG",
            "return_date": "YYYY-AA-GG",  // Gidiş-dönüş ise dönüş tarihi
            "flight_type": "tek_yon veya gidis_donus"
        }
        
        Örnekler:
        Input: "Ankaradan İstanbula 23 Mart 2025'te tek yön"
        Output: {
            "from": "ESB",
            "to": "IST",
            "departure_date": "2025-03-23",
            "return_date": null,
            "flight_type": "tek_yon"
        }
        
        Input: "İstanbul'dan Ankara'ya 25 Mart gidiş 27 Mart dönüş"
        Output: {
            "from": "IST",
            "to": "ESB",
            "departure_date": "2025-03-25",
            "return_date": "2025-03-27",
            "flight_type": "gidis_donus"
        }
        
        Şehir kodlarını doğru kullan:
        - İstanbul: IST
        - Ankara: ESB
        - İzmir: ADB
        
        Tarihleri her zaman YYYY-AA-GG formatında dönüştür.
        Yanıtını her zaman geçerli bir JSON formatında ver.
        """
    
    if not history:
        history.append({"role": "system", "content": system_prompt})
    
    history.append({"role": "user", "content": flight_details})
    
    response = client.chat.completions.create(
        model=llm_name,
        messages=history,
        temperature=0.2,
        response_format={"type": "json_object"}
    )
    
    response_content = response.choices[0].message.content
    history.append({"role": "assistant", "content": response_content})
    
    return response_content, history


def send_message_to_flight_selection_llm(user_message: str, flights: list, history: List[Dict] = None) -> Tuple[str, List[Dict]]:
    """
    Uçuş seçim asistanı LLM'i
    """
    if history is None:
        history = []
        
    system_prompt = """
    Sen bir uçuş seçim asistanısın. Kullanıcının seçtiği uçuşu belirlemelisin.
    Sana uçuş listesi ve kullanıcının seçim mesajı verilecek.
    Kullanıcı herhangi bir bilgi ile bir uçuş seçebilir. Sen kullanıcının söylediği bilgiye göre doğru uçuşu seçmelisin.
    Örneğin kullanıcı "1 numaralı uçuşu istiyorum" derse 1 numaralı uçuşu seç ve aşağıdaki kurala göre yanıt ver.
    Kullanıcı şu saatteki uçuşu istiyorum derse o saatte olan uçuşu bul ve onu seçip aşağıdaki kurala göre yanıt ver.
    Kullanıcı en ucuz uçuşu istiyorum derse en ucuz uçuşu seç ve aşağıdaki kurala göre yanıt ver.
    Kullanıcı en kısa süreli uçuşu istiyorum derse en kısa süreli uçuşu seç ve aşağıdaki kurala göre yanıt ver.
    Kullanıcı şu havayolu uçuşu istiyorum derse o havayolu uçuşları arasından seç ve aşağıdaki kurala göre yanıt ver.
    Kullanıcı şu saatteki uçuşu istiyorum derse o saatte olan uçuşu bul ve onu seçip aşağıdaki kurala göre yanıt ver.
    Kullanıcı en ucuz uçuşu istiyorum derse en ucuz uçuşu seç ve aşağıdaki kurala göre yanıt ver.

    Yanıtını her zaman şu JSON formatında ver:
    {
        "selected_index": x,  // Seçilen uçuşun index numarası (0'dan başlar)
        "explanation": "seçim açıklaması"  // Neden bu uçuşun seçildiği
    }

    Örnek:
    Kullanıcı: "1 numaralı uçuşu istiyorum"
    Yanıt: {
        "selected_index": 0,
        "explanation": "1 numaralı uçuş seçildi"
    }
    
    - Index numarası 0'dan başlar (yani 1. uçuş için 0, 2. uçuş için 1, ...)
    - Eğer kullanıcının isteği anlaşılmazsa selected_index -1 olmalı
    """
    
    try:
        # Uçuş listesini formatlayıp context'e ekle
        flight_context = "\nMevcut uçuşlar:\n"
        for idx, flight in enumerate(flights):
            flight_context += f"\n{idx+1}. Uçuş:\n"
            flight_context += f"Havayolu: {flight['airline']}\n"
            flight_context += f"Kalkış: {flight['date']} {flight['departure_time']}\n"
            flight_context += f"Varış: {flight['date']} {flight['arrival_time']}\n"
            flight_context += f"Fiyat: {flight['price']}\n"
            flight_context += f"Süre: {flight['duration']} dakika\n"
            flight_context += f"Kabin: {flight['cabin_class']}\n"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Uçuş listesi:{flight_context}\n\nKullanıcı mesajı: {user_message}"}
        ]
        
        response = client.chat.completions.create(
            model=llm_name,  # global model değişkenini kullan
            messages=messages,
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        
        if response and response.choices:
            response_content = response.choices[0].message.content
            history.extend(messages)
            history.append({"role": "assistant", "content": response_content})
            return response_content, history
            
        print("LLM'den yanıt alınamadı")
        return None, history
        
    except Exception as e:
        print(f"LLM hatası: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return None, history




def send_message_to_policy_llm(flight: dict, user_input: str = None, history: List[Dict] = None) -> Tuple[str, List[Dict]]:
    """
    Şirket politikalarını kontrol eden LLM fonksiyonu
    """
    if history is None:
        history = []
        
    system_prompt = """
    Sen bir şirket politika kontrol asistanısın. Uçuş seçimlerinin şirket politikalarına uygunluğunu kontrol etmelisin.

    Şirket Politikaları:
    1. Uçuş fiyatı 2000 TL'den fazla olamaz
    2. Sadece Economy sınıfı biletler seçilebilir

    İki tür yanıt verebilirsin:
    1. İlk kontrolde veya yeni bir uçuş seçildiğinde:
       UYGUN: [kısa açıklama]
       veya
       UYGUN_DEGIL: [hangi politikaya aykırı olduğunun açıklaması]

    2. Kullanıcı yanıtını değerlendirirken:
       DEVAM: [kullanıcıya başka seçim için ne söyleneceği]
       veya
       IPTAL: [işlemin neden iptal edildiği]

    Kullanıcının vazgeçtiğini veya olumsuz yanıt verdiğini anlarsan IPTAL döndür.
    Kullanıcı yeni seçim yapmak isterse DEVAM döndür.
    """
    
    if not history:
        history.append({"role": "system", "content": system_prompt})
        # İlk kontrol için uçuş bilgilerini gönder
        flight_context = f"""
        Seçilen uçuş bilgileri:
        Havayolu: {flight['airline']}
        Fiyat: {flight['price']}
        Kabin Sınıfı: {flight['cabin_class']}
        """
        history.append({"role": "user", "content": flight_context})
    else:
        # Kullanıcı yanıtını değerlendir
        history.append({"role": "user", "content": user_input})
    
    response = client.chat.completions.create(
        model=llm_name,
        messages=history,
        temperature=0.2
    )
    
    response_content = response.choices[0].message.content
    history.append({"role": "assistant", "content": response_content})
    
    return response_content, history


def analyze_continuation_intent(user_message: str) -> Tuple[bool, str]:
    """
    Kullanıcının devam etme veya bitirme niyetini analiz eden LLM fonksiyonu
    Args:
        user_message: Kullanıcının mesajı
    Returns:
        Tuple[bool, str]: (devam edilsin mi, yanıt mesajı)
    """
    system_prompt = """
    Sen bir konuşma analiz asistanısın. Kullanıcının mesajını analiz ederek, yeni bir işlem yapmak isteyip istemediğini belirlemelisin.
    
    Kullanıcının mesajını analiz et ve şu formatta yanıt ver:
    {
        "should_continue": true/false,
        "response": "yanıt mesajı"
    }
    
    Eğer kullanıcı:
    - Yeni bir işlem yapmak istiyorsa veya olumlu bir yanıt veriyorsa should_continue: true
    - İşlemi bitirmek istiyorsa veya olumsuz bir yanıt veriyorsa should_continue: false
    
    Yanıt mesajı:
    - Devam edilecekse: Yeni aramaya yönelik bir mesaj
    - Bitirilecekse: Nazik bir veda mesajı
    """
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ]
    
    try:
        response = client.chat.completions.create(
            model=llm_name,
            messages=messages,
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        return result["should_continue"], result["response"]
        
    except Exception as e:
        print(f"LLM analiz hatası: {str(e)}")
        return True, "Üzgünüm, bir hata oluştu. Size nasıl yardımcı olabilirim?"