from openai import OpenAI
import json
from typing import List, Dict, Tuple, Optional
import os 
from all_llms import send_message_to_flight_llm, send_message_to_flight_search_llm
from flight_searcher import search_flights
from flask import session

llm_api_key = os.getenv("LLM_API_KEY")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key= llm_api_key
)

def get_flight_info(user_message: str, history: List[Dict] = None) -> Tuple[Optional[str], Optional[str], List[Dict]]:
    """
    Kullanıcıdan uçuş bilgilerini alan ve eksik bilgileri tamamlayan fonksiyon
    Args:
        user_message: Kullanıcının mesajı
        history: Mevcut sohbet geçmişi (opsiyonel)
    Returns:
        Tuple[Optional[str], Optional[str], List[Dict]]: 
        - flight_details: Tamamlanmış uçuş detayları veya None
        - needs_confirmation: Onay/hata mesajı veya None
        - history: Güncellenmiş mesaj geçmişi
    """
    if history is None:
        history = []
    
    response, history = send_message_to_flight_llm(user_message, history)
    
    # JSON yanıtını kontrol et
    try:
        json_response = json.loads(response)
        if "TAMAM" in json_response:
            return json_response["TAMAM"], None, history
        elif "ONAY" in json_response:
            return None, json_response["ONAY"], history
        elif "EKSİK" in json_response:
            return None, f"Lütfen şu bilgileri de belirtin: {json_response['EKSİK']}", history
    except json.JSONDecodeError:
        # JSON değilse string kontrolü yap
        if response.startswith("TAMAM:"):
            return response.replace("TAMAM:", "").strip(), None, history
        elif response.startswith("ONAY:"):
            return None, response.replace("ONAY:", "").strip(), history
        else:
            return None, response.replace("EKSİK:", "").strip(), history
    
    return None, None, history



def find_flights(flight_details: str) -> tuple:
    """
    Verilen uçuş detaylarına göre uygun uçuşları bulan fonksiyon
    Args:
        flight_details: get_flight_info'dan gelen uçuş detayları
    Returns:
        tuple: (gidiş uçuşları listesi, dönüş uçuşları listesi, gidiş-dönüş mü bool)
    """
    try:
        # LLM'den formatlanmış bilgileri al
        response, _ = send_message_to_flight_search_llm(flight_details)
        print("\nLLM yanıtı:", response)  # Debug için
        
        # Markdown formatını temizle
        if response.startswith("```"):
            response = response.split("```")[1]
            if response.startswith("json"):
                response = response[4:].strip()
        
        try:
            parsed_details = json.loads(response)
            print("\nParse edilen detaylar:", parsed_details)  # Debug için
            
            # Gidiş uçuşlarını ara
            outbound_flights = search_flights(
                fromEntityId=parsed_details.get("from"),
                toEntityId=parsed_details.get("to"),
                departDate=parsed_details.get("departure_date"),
                max_results=5
            )
            
            # Gidiş-dönüş kontrolü
            is_round_trip = parsed_details.get("flight_type") == "gidis_donus"
            return_flights = []
            
            if is_round_trip and parsed_details.get("return_date"):
                print(f"\nDönüş tarihi: {parsed_details['return_date']}")  # Debug için
                # Dönüş uçuşlarını ara - aynı fonksiyonu kullan, sadece şehirleri değiştir
                return_flights = search_flights(
                    fromEntityId=parsed_details.get("to"),  # Varış noktasından
                    toEntityId=parsed_details.get("from"),  # Kalkış noktasına
                    departDate=parsed_details.get("return_date"),  # Dönüş tarihi
                    max_results=5
                )
                print(f"\nBulunan dönüş uçuşları: {len(return_flights) if return_flights else 0}")
            
            if not outbound_flights:
                print("Gidiş uçuşu bulunamadı")
                return [], [], False
                
            if is_round_trip and not return_flights:
                print("Dönüş uçuşu bulunamadı")
                return [], [], False
                
            return outbound_flights, return_flights, is_round_trip
            
        except json.JSONDecodeError as e:
            print(f"JSON parse hatası: {str(e)}")
            return [], [], False
        
    except Exception as e:
        print(f"Beklenmeyen hata: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return [], [], False 


if __name__ == "__main__":
    flight_details = get_flight_info()
    print("\nUçuş detayları:", flight_details)
    
    flights = find_flights(flight_details)
    print("\nFormatlanmış detaylar:")
    print(flights)

























