from functions import get_flight_info, find_flights
from all_llms import send_message_to_flight_selection_llm, send_message_to_policy_llm
from typing import List, Dict
import json 

def select_flight(flights: list, user_message: str, history: List[Dict] = None) -> dict:
    """
    LLM kullanarak uçuş seçimi yapan fonksiyon
    """
    try:
        response, history = send_message_to_flight_selection_llm(user_message, flights, history)
        
        if not response:
            print("LLM'den yanıt alınamadı")
            return None
            
        print(f"LLM yanıtı: {response}")  # Debug için
        
        try:
            # Markdown formatını temizle
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:].strip()
            
            # JSON parse et
            selection = json.loads(response)
            selected_index = selection.get('selected_index', -1)
            
            if selected_index >= 0 and selected_index < len(flights):
                selected_flight = flights[selected_index]
                print(f"Seçilen uçuş: {selected_flight['airline']} {selected_flight['departure_time']}")
                return selected_flight
            
            print(f"Geçersiz index: {selected_index}")
            return None
            
        except json.JSONDecodeError as e:
            print(f"JSON parse hatası: {str(e)}")
            # Sayısal girdi kontrolü
            if user_message.isdigit():
                index = int(user_message) - 1
                if 0 <= index < len(flights):
                    return flights[index]
            return None
            
    except Exception as e:
        print(f"Uçuş seçim hatası: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return None
    
    
def check_flight_policy(flights, selected_flight: dict) -> bool:
    """
    Seçilen uçuşun şirket politikalarına uygunluğunu kontrol eden fonksiyon
    Args:
        selected_flight: Seçilen uçuş bilgileri
    Returns:
        bool: Politikalara uygunsa True, değilse False
    """
    try:
        print("\nPolicy check için seçilen uçuş:")
        print(f"Fiyat: {selected_flight.get('price')}")
        print(f"Kabin: {selected_flight.get('cabin_class')}")
        
        # İlk kontrol
        response, _ = send_message_to_policy_llm(selected_flight)
        print(f"\nLLM policy check yanıtı: {response}")
        
        if response.startswith("UYGUN:"):
            print("Politika kontrolü başarılı: Uçuş uygun")
            return True
            
        elif response.startswith("UYGUN_DEGIL:"):
            explanation = response.replace("UYGUN_DEGIL:", "").strip()
            print(f"Politika kontrolü başarısız: {explanation}")
            return False
            
        elif response.startswith("DEVAM:"):
            message = response.replace("DEVAM:", "").strip()
            print(f"Politika kontrolü devam mesajı: {message}")
            return False
                
        elif response.startswith("IPTAL:"):
            message = response.replace("IPTAL:", "").strip()
            print(f"Politika kontrolü iptal mesajı: {message}")
            return False
            
        print(f"Bilinmeyen yanıt formatı: {response}")
        return False  # Varsayılan olarak False dön
        
    except Exception as e:
        print(f"Policy check hatası: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return False


# def main():
#     flight_details = get_flight_info()
#     print("\nUçuş detayları:", flight_details)

#     flights = find_flights(flight_details)
#     selected_flight = select_flight(flights)
#     return selected_flight

# if __name__ == "__main__":
#     selected_flight = main()
#     if selected_flight:
#         print("\nİşlem tamamlandı. Seçilen uçuş bilgileri:")
#         print(selected_flight)