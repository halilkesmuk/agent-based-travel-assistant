from flask import Flask, render_template, request, jsonify, session
from functions import get_flight_info, find_flights
from controller import select_flight, check_flight_policy
from all_llms import analyze_continuation_intent

app = Flask(__name__)
app.secret_key = '1a2b3c'  # Session için gerekli

# Akış durumunu takip etmek için state'ler
STATES = {
    'INITIAL': 0,
    'COLLECTING_FLIGHT_INFO': 1, 
    'SHOWING_FLIGHTS': 2,
    'SELECTING_FLIGHT': 3,
    'CHECKING_POLICY': 4,
    'SHOWING_RETURN_FLIGHTS': 5,  # Dönüş uçuşlarını gösterme
    'SELECTING_RETURN_FLIGHT': 6,  # Dönüş uçuşu seçimi
    'CHECKING_RETURN_POLICY': 7,   # Dönüş uçuşu policy kontrolü
    'COMPLETED': 8
}

@app.route('/')
def home():
    # Yeni oturum başlat
    session['state'] = STATES['INITIAL']
    session['flight_details'] = None
    session['flights'] = None
    session['return_flights'] = None  # Dönüş uçuşları için
    session['selected_flight'] = None
    session['selected_return_flight'] = None  # Seçilen dönüş uçuşu için
    session['is_round_trip'] = False  # Gidiş-dönüş kontrolü için
    session['chat_history'] = []  # History'yi ekle
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json['message']
    current_state = session.get('state', STATES['INITIAL'])
    
    # Retrieve chat history from session
    history = session.get('chat_history', [])
    
    if current_state == STATES['INITIAL']:
        # Start collecting flight information
        session['state'] = STATES['COLLECTING_FLIGHT_INFO']
        return jsonify({
            'response': 'Merhaba! Size nasıl yardımcı olabilirim?',
            'state': 'collecting_info'
        })
    
    elif current_state == STATES['COLLECTING_FLIGHT_INFO']:
        # Collect flight information
        flight_details, needs_confirmation, history = get_flight_info(user_message, history)
        
        # Save updated history to session
        session['chat_history'] = history
        
        if needs_confirmation:
            return jsonify({
                'response': needs_confirmation,
                'state': 'collecting_info'
            })
        
        if flight_details:
            session['flight_details'] = flight_details
            outbound_flights, return_flights, is_round_trip = find_flights(flight_details)
            print("Bulunan uçuşlar:", outbound_flights)
            if not outbound_flights:
                # No flights found, reset to initial state
                session['state'] = STATES['INITIAL']
                return jsonify({
                    'response': 'Üzgünüm, uygun uçuş bulunamadı. Başka bir arama yapmak ister misiniz?',
                    'state': 'initial'
                })
            
            # Gidiş-dönüş kontrolü ve uçuşları kaydet
            session['flights'] = outbound_flights
            session['return_flights'] = return_flights
            session['is_round_trip'] = is_round_trip
            session['state'] = STATES['SHOWING_FLIGHTS']
            
            response_text = 'Bulunan gidiş uçuşları:\n' + format_flights(outbound_flights)
            if is_round_trip:
                response_text += '\n\nÖnce gidiş uçuşunuzu seçin, dönüş uçuşlarını daha sonra göstereceğim.'
            
            return jsonify({
                'response': response_text,
                'state': 'showing_flights'
            })
        
        # If information is still missing, provide feedback
        return jsonify({
            'response': f'{flight_details} \n Lütfen eksik bilgileri tamamlayın.',
            'state': 'collecting_info'
        })
    
    elif current_state == STATES['SHOWING_FLIGHTS']:
        # Handle flight selection
        selected = select_flight(session['flights'], user_message, history)
        
        if selected:
            session['selected_flight'] = selected
            session['state'] = STATES['CHECKING_POLICY']
            return jsonify({
                'response': f"Seçilen uçuş:\n{format_flight(selected)}\nŞirket politikalarını kontrol etmemi ister misiniz?",
                'state': 'checking_policy',
                'selected_flight': selected  # Seçilen uçuşu da gönder
            })
        else:
            # If the user wants to exit, reset to initial state
            if user_message.lower() in ['çıkmak istiyorum', 'vazgeç', 'iptal']:
                session['state'] = STATES['INITIAL']
                return jsonify({
                    'response': 'İşlem iptal edildi. Yeni bir arama yapmak ister misiniz?',
                    'state': 'initial'
                })
            # Invalid selection, show flights again
            return jsonify({
                'response': 'Geçerli bir uçuş seçilmedi. Lütfen aşağıdaki uçuşlardan birini seçin:\n' + format_flights(session['flights']),
                'state': 'showing_flights'
            })
    
    elif current_state == STATES['CHECKING_POLICY']:
        # Check flight policy
        policy_check_result = check_flight_policy(session['flights'], session['selected_flight'])
        if policy_check_result:
            if session.get('is_round_trip', False):
                # Gidiş-dönüş ise, dönüş uçuşlarını göster
                session['state'] = STATES['SHOWING_RETURN_FLIGHTS']
                return jsonify({
                    'response': 'Gidiş uçuşunuz onaylandı! Şimdi dönüş uçuşlarını gösteriyorum:\n' + format_flights(session['return_flights']),
                    'state': 'showing_return_flights'
                })
            else:
                # Tek yön ise tamamla
                session['state'] = STATES['COMPLETED']
                return jsonify({
                    'response': 'Uçuş rezervasyonunuz onaylandı! Başka bir işlem yapmak ister misiniz?',
                    'state': 'completed',
                    'selected_flight': session['selected_flight']
                })
        else:
            # If the policy check fails, provide a detailed explanation and show flights again
            session['state'] = STATES['SHOWING_FLIGHTS']
            return jsonify({
                'response': 'Üzgünüm, seçilen uçuş şirket politikalarına uygun değil. Lütfen başka bir uçuş seçin:\n' + format_flights(session['flights']),
                'state': 'showing_flights',
                'flights': session['flights']
            })
            
    elif current_state == STATES['SHOWING_RETURN_FLIGHTS']:
        # Handle return flight selection
        selected_return = select_flight(session['return_flights'], user_message, history)
        
        if selected_return:
            session['selected_return_flight'] = selected_return
            session['state'] = STATES['CHECKING_RETURN_POLICY']
            return jsonify({
                'response': f"Seçilen dönüş uçuşu:\n{format_flight(selected_return)}\nŞirket politikalarını kontrol etmemi ister misiniz?",
                'state': 'checking_return_policy',
                'selected_return_flight': selected_return
            })
        else:
            # Invalid selection, show return flights again
            return jsonify({
                'response': 'Geçerli bir uçuş seçilmedi. Lütfen aşağıdaki dönüş uçuşlarından birini seçin:\n' + format_flights(session['return_flights']),
                'state': 'showing_return_flights'
            })
            
    elif current_state == STATES['CHECKING_RETURN_POLICY']:
        # Check return flight policy
        policy_check_result = check_flight_policy(session['return_flights'], session['selected_return_flight'])
        if policy_check_result:
            session['state'] = STATES['COMPLETED']
            return jsonify({
                'response': 'Gidiş ve dönüş uçuşlarınız onaylandı! Başka bir işlem yapmak ister misiniz?',
                'state': 'completed',
                'selected_flight': session['selected_flight'],
                'selected_return_flight': session['selected_return_flight']
            })
        else:
            # If the policy check fails, show return flights again
            session['state'] = STATES['SHOWING_RETURN_FLIGHTS']
            return jsonify({
                'response': 'Üzgünüm, seçilen dönüş uçuşu şirket politikalarına uygun değil. Lütfen başka bir uçuş seçin:\n' + format_flights(session['return_flights']),
                'state': 'showing_return_flights',
                'return_flights': session['return_flights']
            })
    
    elif current_state == STATES['COMPLETED']:
        # LLM ile kullanıcının niyetini analiz et
        should_continue, response = analyze_continuation_intent(user_message)
        
        if not should_continue:
            return jsonify({
                'response': response,
                'state': 'terminated'
            })
        else:
            # Reset to initial state for new search
            session['state'] = STATES['INITIAL']
            session['flight_details'] = None
            session['flights'] = None
            session['return_flights'] = None
            session['selected_flight'] = None
            session['selected_return_flight'] = None
            session['is_round_trip'] = False
            session['chat_history'] = []
            return jsonify({
                'response': response,
                'state': 'initial'
            })

def format_flights(flights):
    """Uçuşları formatlı şekilde göster"""
    result = "Bulunan uçuşlar:\n"
    for idx, flight in enumerate(flights, 1):
        result += f"\n{idx}. Uçuş:\n"
        result += format_flight(flight)
        result += "\n" + "-"*50
    return result

def format_flight(flight):
    """Tek uçuşu formatlı şekilde göster"""
    return f"""➡️  {flight['from']} ✈️  {flight['to']}
🛫 {flight['airline']}
💰 {flight['price']}
⏰ Kalkış: {flight['date']} - {flight['departure_time']}
⏰ Varış: {flight['date']} - {flight['arrival_time']}
⌛ Süre: {flight['duration']} dakika
💺 {flight['cabin_class']}"""

if __name__ == '__main__':
    app.run(debug=True)