from flask import Blueprint, render_template, request, session
import numpy as np
import requests
import colorsys
import io

ml = Blueprint('ml', __name__)

# ============================================
# CONFIGURATION
# ============================================
WEATHER_API_KEY = 'ac2393b20e59d2176ba0938bc79029e3'

# ============================================
# CROP PRICE DATABASE
# ============================================
CROP_BASE_PRICES = {
    'tomato': 25, 'potato': 15, 'onion': 20,
    'wheat': 22, 'rice': 35, 'corn': 18,
    'carrot': 30, 'spinach': 40, 'mango': 60,
    'banana': 25, 'apple': 80, 'grapes': 70,
    'cauliflower': 35, 'cabbage': 20, 'brinjal': 28,
    'okra': 32, 'peas': 45, 'garlic': 90,
    'ginger': 80, 'orange': 55, 'papaya': 30,
    'watermelon': 18, 'chilli': 120, 'cucumber': 22,
    'pumpkin': 15, 'radish': 18, 'beetroot': 25,
    'rose': 150 , 'marigold': 40, 'jasmine': 200,
    'lotus': 180, 'sunflower': 80, 'tuberose': 120,
    'chrysanthemum': 90, 'gerbera': 100, 'lily': 160,
    'mogra': 250, 'crossandra': 60, 'aster': 70,
}

SEASON_MULTIPLIER = {
    'summer': 1.2, 'winter': 0.9,
    'monsoon': 1.1, 'spring': 1.0
}


# ============================================
# LOCAL CROP DETECTION — Zero API Needed
# ============================================
def detect_crop_from_image(image_bytes, media_type):
    try:
        from PIL import Image

        image = Image.open(io.BytesIO(image_bytes))
        image = image.convert('RGB')
        image = image.resize((100, 100))

        pixels = list(image.getdata())

        avg_r = sum(p[0] for p in pixels) / len(pixels)
        avg_g = sum(p[1] for p in pixels) / len(pixels)
        avg_b = sum(p[2] for p in pixels) / len(pixels)

        h, s, v = colorsys.rgb_to_hsv(
            avg_r / 255, avg_g / 255, avg_b / 255
        )
        h_deg = h * 360

        print(f"[DETECTION] R:{avg_r:.0f} G:{avg_g:.0f} B:{avg_b:.0f} H:{h_deg:.0f} S:{s:.2f} V:{v:.2f}")

        # Red — Tomato or Chilli
        if (h_deg < 15 or h_deg > 345) and s > 0.4:
            if v < 0.5:
                return 'chilli'
            return 'tomato'

        # Orange — Orange or Carrot
        elif 15 <= h_deg < 40 and s > 0.4:
            if avg_b < 60:
                return 'carrot'
            return 'orange'

        # Yellow — Banana or Corn
        elif 40 <= h_deg < 70 and s > 0.3:
            if avg_g > avg_r:
                return 'corn'
            return 'banana'

        # Yellow-Green — Peas or Okra
        elif 70 <= h_deg < 100 and s > 0.3:
            if v > 0.7:
                return 'peas'
            return 'okra'

        # Green — Spinach, Cabbage, Cucumber
        elif 100 <= h_deg < 150 and s > 0.25:
            if v > 0.6:
                return 'cucumber'
            elif avg_g > 130:
                return 'spinach'
            return 'cabbage'

        # Purple — Brinjal or Beetroot
        elif 250 <= h_deg < 320 and s > 0.3:
            if avg_r > avg_b:
                return 'beetroot'
            return 'brinjal'

        # White/Pale — Cauliflower or Garlic
        elif s < 0.15 and v > 0.75:
            if avg_g > avg_b:
                return 'cauliflower'
            return 'garlic'

        # Brown/Earthy — Potato, Onion, Ginger
        elif 20 <= h_deg < 40 and s < 0.4 and v < 0.7:
            if avg_r > 160:
                return 'onion'
            elif avg_r > 120:
                return 'potato'
            return 'ginger'

        # Dark Green — Watermelon or Pumpkin
        elif 100 <= h_deg < 150 and s > 0.3 and v < 0.4:
            if avg_g > avg_r + 20:
                return 'watermelon'
            return 'pumpkin'

        # Pink/Light Red — Watermelon inside or Papaya
        elif (h_deg < 20 or h_deg > 330) and s > 0.2 and v > 0.7:
            if avg_b > 80:
                return 'papaya'
            return 'watermelon'

        # Deep Yellow-Orange — Mango
        elif 30 <= h_deg < 55 and s > 0.5 and v > 0.6:
            return 'mango'

        # Grains — Wheat or Rice (golden/pale)
        elif 30 <= h_deg < 60 and s < 0.3 and v > 0.6:
            if avg_r > avg_g:
                return 'wheat'
            return 'rice'

        # Purple-Red — Grapes
        elif 280 <= h_deg < 340 and s > 0.25 and v < 0.5:
            return 'grapes'

        # Radish — White with pink tinge
        elif s < 0.2 and avg_r > avg_b + 10:
            return 'radish'

        # Default fallback
        else:
            return 'tomato'

    except Exception as e:
        print(f"[DETECTION ERROR] {e}")
        return None


# ============================================
# WEATHER API
# ============================================
def get_weather(city):
    try:
        url = f'https://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric'
        response = requests.get(url, timeout=5)
        data = response.json()
        if response.status_code == 200:
            weather = {
                'city': city,
                'temp': round(data['main']['temp']),
                'humidity': data['main']['humidity'],
                'description': data['weather'][0]['description'].title(),
                'icon': data['weather'][0]['icon'],
                'wind': data['wind']['speed'],
                'feels_like': round(data['main']['feels_like'])
            }
            weather['advisory'] = generate_advisory(weather)
            return weather
    except Exception as e:
        print(f"[WEATHER ERROR] {e}")
        return None


def generate_advisory(weather):
    advisories = []
    temp = weather['temp']
    humidity = weather['humidity']
    desc = weather['description'].lower()

    if 'rain' in desc:
        advisories.append("Rain detected — harvest moisture-sensitive crops immediately.")
    if temp > 38:
        advisories.append("High temperature alert — increase irrigation frequency today.")
    if temp < 12:
        advisories.append("Cold conditions — protect frost-sensitive crops with covering.")
    if humidity > 80:
        advisories.append("High humidity — watch for fungal diseases on crops.")
    if humidity < 30:
        advisories.append("Dry conditions — ideal for grain storage this week.")
    if 'clear' in desc:
        advisories.append("Clear weather — excellent conditions for harvesting and drying.")
    if not advisories:
        advisories.append("Weather conditions normal — continue regular farming activities.")

    return advisories


# ============================================
# MAIN PREDICTOR ROUTE
# ============================================
@ml.route('/price-predictor', methods=['GET', 'POST'])
def price_predictor():
    prediction = None
    weather = None
    detected_crop = None
    error_message = None

    # Get weather for farmer's location
    weather = None


    if request.method == 'POST':
        season = request.form.get('season', '').lower()
        quantity = float(request.form.get('quantity', 1))
        crop_name = None

        # Detect crop from uploaded image
        if 'crop_image' in request.files:
            file = request.files['crop_image']
            if file and file.filename != '':

                filename = file.filename.lower()
                if filename.endswith('.png'):
                    media_type = 'image/png'
                elif filename.endswith('.webp'):
                    media_type = 'image/webp'
                else:
                    media_type = 'image/jpeg'

                image_bytes = file.read()
                detected = detect_crop_from_image(image_bytes, media_type)

                if detected:
                    detected_crop = detected
                    crop_name = detected
                else:
                    error_message = "Could not analyze this image. Please try a clearer photo."

        # Calculate price prediction
        if crop_name and season:
            base_price = CROP_BASE_PRICES.get(crop_name, 28)
            multiplier = SEASON_MULTIPLIER.get(season, 1.0)

            # Weather adjustment
            weather_adjustment = 1.0
            if weather:
                if weather['humidity'] > 75:
                    weather_adjustment = 1.08
                if weather['temp'] > 38:
                    weather_adjustment = 1.12

            noise = np.random.uniform(-1.5, 1.5)
            predicted_price = round(
                (base_price * multiplier * weather_adjustment) + noise, 2
            )

            prediction = {
                'crop': crop_name.title(),
                'season': season.title(),
                'price': predicted_price,
                'total': round(predicted_price * quantity, 2),
                'quantity': quantity,
                'min_price': round(predicted_price - 3, 2),
                'max_price': round(predicted_price + 4, 2),
                'weather_adjusted': weather is not None,
                'ai_detected': detected_crop is not None
            }

        elif not crop_name and not error_message:
            error_message = "Please upload a crop photo to get price prediction."

    return render_template('ml/predictor.html',
                         prediction=prediction,
                         weather=weather,
                         detected_crop=detected_crop,
                         error_message=error_message)


# ============================================
# TEST ROUTE — Remove after testing
# ============================================
@ml.route('/test-vision')
def test_vision():
    return "Local detection active — no API needed!"

@ml.route('/best-time-to-sell', methods=['GET', 'POST'])
def best_time_to_sell():
    result = None

    MONTHLY_PATTERNS = {
        'tomato': {
            1: 35, 2: 30, 3: 22, 4: 18, 5: 20,
            6: 28, 7: 32, 8: 35, 9: 30, 10: 25,
            11: 28, 12: 32
        },
        'onion': {
            1: 25, 2: 20, 3: 18, 4: 22, 5: 30,
            6: 35, 7: 40, 8: 38, 9: 30, 10: 22,
            11: 20, 12: 22
        },
        'potato': {
            1: 18, 2: 15, 3: 12, 4: 14, 5: 18,
            6: 20, 7: 22, 8: 20, 9: 16, 10: 14,
            11: 15, 12: 17
        },
        'wheat': {
            1: 22, 2: 20, 3: 18, 4: 25, 5: 28,
            6: 26, 7: 24, 8: 22, 9: 20, 10: 21,
            11: 22, 12: 23
        },
        'mango': {
            1: 80, 2: 75, 3: 60, 4: 45, 5: 40,
            6: 55, 7: 70, 8: 80, 9: 85, 10: 90,
            11: 95, 12: 88
        },
        'rice': {
            1: 38, 2: 36, 3: 34, 4: 35, 5: 38,
            6: 40, 7: 38, 8: 35, 9: 30, 10: 28,
            11: 32, 12: 36
        },
        'rose': {
            1: 180, 2: 200, 3: 160, 4: 140, 5: 130,
            6: 120, 7: 130, 8: 140, 9: 150, 10: 160,
            11: 180, 12: 200
        },
        'marigold': {
            1: 50, 2: 45, 3: 35, 4: 30, 5: 28,
            6: 30, 7: 35, 8: 40, 9: 50, 10: 80,
            11: 100, 12: 90
        },
        'jasmine': {
            1: 180, 2: 160, 3: 150, 4: 140, 5: 160,
            6: 200, 7: 220, 8: 210, 9: 190, 10: 180,
            11: 200, 12: 220
        },
    }

    MONTH_NAMES = {
        1: 'January', 2: 'February', 3: 'March',
        4: 'April', 5: 'May', 6: 'June',
        7: 'July', 8: 'August', 9: 'September',
        10: 'October', 11: 'November', 12: 'December'
    }

    # Define BEFORE if block — always available
    crops_available = [
        'tomato', 'onion', 'potato',
        'wheat', 'mango', 'rice',
        'rose', 'marigold', 'jasmine'
    ]

    if request.method == 'POST':
        crop = request.form.get('crop', '').lower()
        quantity = float(request.form.get('quantity', 100))

        if crop in MONTHLY_PATTERNS:
            prices = MONTHLY_PATTERNS[crop]
            best_month = max(prices, key=prices.get)
            worst_month = min(prices, key=prices.get)
            current_month = __import__('datetime').datetime.now().month

            trend_data = [
                {'month': MONTH_NAMES[m], 'price': prices[m]}
                for m in range(1, 13)
            ]

            future_months = {}
            for m in range(current_month, current_month + 6):
                actual_month = ((m - 1) % 12) + 1
                future_months[MONTH_NAMES[actual_month]] = prices[actual_month]

            best_upcoming = max(future_months, key=future_months.get)

            result = {
                'crop': crop.title(),
                'quantity': quantity,
                'best_month': MONTH_NAMES[best_month],
                'best_price': prices[best_month],
                'worst_month': MONTH_NAMES[worst_month],
                'worst_price': prices[worst_month],
                'current_month': MONTH_NAMES[current_month],
                'current_price': prices[current_month],
                'best_upcoming': best_upcoming,
                'best_upcoming_price': future_months[best_upcoming],
                'trend_data': trend_data,
                'best_earning': round(prices[best_month] * quantity, 2),
                'current_earning': round(prices[current_month] * quantity, 2),
                'extra_earning': round(
                    (prices[best_month] - prices[current_month]) * quantity, 2
                )
            }

    return render_template('ml/best_time.html',
                         result=result,
                         crops_available=crops_available)


                         
# ============================================================
# PASTE THIS ENTIRE BLOCK into routes/ml.py
# Replace your existing get_weather_by_coords route AND
# the generate_advisory function with this complete version
# ============================================================

# ---- ADD THIS IMPORT at the top of ml.py if not already there ----
# from flask import jsonify

@ml.route('/get-weather-by-coords')
def get_weather_by_coords():
    from flask import jsonify
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)

    if not lat or not lon:
        return jsonify({'success': False, 'error': 'No coordinates provided'})

    # ── STRATEGY 1: OpenWeatherMap by EXACT lat/lon (never city name) ──
    weather = None
    try:
        url = (
            f'https://api.openweathermap.org/data/2.5/weather'
            f'?lat={lat}&lon={lon}'
            f'&appid={WEATHER_API_KEY}'
            f'&units=metric'
        )
        resp = requests.get(url, timeout=6)
        data = resp.json()

        if resp.status_code == 200:
            # Build precise location label using reverse geocode
            city_name = _reverse_geocode(lat, lon) or data.get('name', 'Your Location')

            weather = {
                'city':        city_name,
                'lat':         round(lat, 4),
                'lon':         round(lon, 4),
                'temp':        round(data['main']['temp']),
                'feels_like':  round(data['main']['feels_like']),
                'humidity':    data['main']['humidity'],
                'description': data['weather'][0]['description'].title(),
                'icon':        data['weather'][0]['icon'],
                'wind':        round(data['wind']['speed'], 1),
                'pressure':    data['main']['pressure'],
                'source':      'OpenWeatherMap'
            }
        else:
            raise Exception(f"OWM status {resp.status_code}")

    except Exception as e:
        print(f"[WEATHER OWM ERROR] {e}")

    # ── STRATEGY 2: Open-Meteo fallback (no API key, very accurate) ──
    if not weather:
        try:
            weather = _get_weather_open_meteo(lat, lon)
        except Exception as e:
            print(f"[WEATHER OPEN-METEO ERROR] {e}")

    if not weather:
        return jsonify({'success': False, 'error': 'Weather service unavailable'})

    weather['advisory'] = _generate_advisory(weather)

    return jsonify({'success': True, 'weather': weather})


def _reverse_geocode(lat, lon):
    """
    Use OpenWeatherMap Reverse Geocoding to get the precise
    village/town name for given coordinates — avoids wrong city matching.
    """
    try:
        url = (
            f'https://api.openweathermap.org/geo/1.0/reverse'
            f'?lat={lat}&lon={lon}&limit=1'
            f'&appid={WEATHER_API_KEY}'
        )
        resp = requests.get(url, timeout=5)
        results = resp.json()
        if results and len(results) > 0:
            place = results[0]
            # Build: "Kavalapur, Sangli, Maharashtra"
            parts = []
            if place.get('name'):
                parts.append(place['name'])
            if place.get('state'):
                parts.append(place['state'])
            return ', '.join(parts) if parts else None
    except Exception as e:
        print(f"[REVERSE GEOCODE ERROR] {e}")
    return None


def _get_weather_open_meteo(lat, lon):
    """
    Fallback: Open-Meteo API — completely free, no API key,
    uses NWP model data tied to exact coordinates.
    """
    # Step 1 — Get current weather
    weather_url = (
        f'https://api.open-meteo.com/v1/forecast'
        f'?latitude={lat}&longitude={lon}'
        f'&current=temperature_2m,relative_humidity_2m,apparent_temperature,'
        f'weather_code,wind_speed_10m,surface_pressure'
        f'&wind_speed_unit=ms'
        f'&timezone=Asia%2FKolkata'
    )
    resp = requests.get(weather_url, timeout=8)
    data = resp.json()

    current = data.get('current', {})
    code = current.get('weather_code', 0)

    # Step 2 — Reverse geocode for city name
    city_name = _reverse_geocode_nominatim(lat, lon) or f'{round(lat,2)}°N, {round(lon,2)}°E'

    return {
        'city':        city_name,
        'lat':         round(lat, 4),
        'lon':         round(lon, 4),
        'temp':        round(current.get('temperature_2m', 0)),
        'feels_like':  round(current.get('apparent_temperature', 0)),
        'humidity':    current.get('relative_humidity_2m', 0),
        'description': _wmo_code_to_description(code),
        'icon':        _wmo_code_to_icon(code),
        'wind':        round(current.get('wind_speed_10m', 0), 1),
        'pressure':    round(current.get('surface_pressure', 1013)),
        'source':      'Open-Meteo'
    }


def _reverse_geocode_nominatim(lat, lon):
    """OpenStreetMap Nominatim — free, no key needed."""
    try:
        url = (
            f'https://nominatim.openstreetmap.org/reverse'
            f'?lat={lat}&lon={lon}&format=json&zoom=10'
        )
        headers = {'User-Agent': 'AgroConnect/1.0 (agroconnect@example.com)'}
        resp = requests.get(url, timeout=5, headers=headers)
        data = resp.json()
        addr = data.get('address', {})
        parts = []
        # Village/suburb first, then district
        for key in ['village', 'suburb', 'town', 'city', 'county', 'state_district', 'state']:
            if addr.get(key):
                parts.append(addr[key])
                if len(parts) == 2:
                    break
        return ', '.join(parts) if parts else None
    except Exception as e:
        print(f"[NOMINATIM ERROR] {e}")
    return None


def _wmo_code_to_description(code):
    """Convert WMO weather code to human description."""
    WMO = {
        0: 'Clear Sky', 1: 'Mainly Clear', 2: 'Partly Cloudy', 3: 'Overcast',
        45: 'Fog', 48: 'Depositing Rime Fog',
        51: 'Light Drizzle', 53: 'Moderate Drizzle', 55: 'Heavy Drizzle',
        61: 'Slight Rain', 63: 'Moderate Rain', 65: 'Heavy Rain',
        71: 'Slight Snow', 73: 'Moderate Snow', 75: 'Heavy Snow',
        80: 'Slight Rain Showers', 81: 'Moderate Rain Showers', 82: 'Violent Rain Showers',
        95: 'Thunderstorm', 96: 'Thunderstorm with Hail', 99: 'Heavy Thunderstorm',
    }
    return WMO.get(code, 'Variable Conditions')


def _wmo_code_to_icon(code):
    """Map WMO code to OpenWeatherMap icon code for UI consistency."""
    if code == 0:   return '01d'
    if code == 1:   return '01d'
    if code == 2:   return '02d'
    if code == 3:   return '04d'
    if code in (45, 48): return '50d'
    if code in (51, 53, 55): return '09d'
    if code in (61, 63, 65): return '10d'
    if code in (71, 73, 75): return '13d'
    if code in (80, 81, 82): return '09d'
    if code in (95, 96, 99): return '11d'
    return '03d'


def _generate_advisory(weather):
    """Generate farming advisories based on actual weather data."""
    advisories = []
    temp     = weather.get('temp', 25)
    humidity = weather.get('humidity', 50)
    wind     = weather.get('wind', 0)
    desc     = weather.get('description', '').lower()

    # Rain advisories
    if any(w in desc for w in ['rain', 'drizzle', 'shower']):
        advisories.append('🌧 Rain detected — harvest moisture-sensitive crops immediately and cover stored grain.')

    # Thunderstorm
    if 'thunder' in desc:
        advisories.append('⚡ Thunderstorm warning — avoid open fields and protect equipment.')

    # Temperature
    if temp >= 40:
        advisories.append('🌡 Extreme heat ({}°C) — water crops in early morning and late evening only.'.format(temp))
    elif temp >= 35:
        advisories.append('☀️ High temperature ({}°C) — increase irrigation frequency today.'.format(temp))
    elif temp <= 10:
        advisories.append('❄️ Cold conditions ({}°C) — protect frost-sensitive crops with mulch or covering.'.format(temp))

    # Humidity
    if humidity >= 80:
        advisories.append('💧 High humidity ({}%) — watch for fungal diseases, especially on tomato and grapes.'.format(humidity))
    elif humidity <= 25:
        advisories.append('🏜 Very dry air ({}% humidity) — ideal conditions for grain storage and drying crops.'.format(humidity))

    # Wind
    if wind >= 10:
        advisories.append('💨 Strong winds ({} m/s) — support tall crops like sugarcane and delay spraying.'.format(wind))

    # Clear weather
    if any(w in desc for w in ['clear', 'sunny', 'mainly clear']):
        advisories.append('🌤 Clear sky — excellent conditions for harvesting, drying, and field spraying.')

    if not advisories:
        advisories.append('✅ Weather conditions normal for {}. Continue regular farming activities.'.format(
            weather.get('city', 'your area').split(',')[0]
        ))

    return advisories