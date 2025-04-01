import alpaca_trade_api as tradeapi
import yfinance as yf
import time

# 알파카 API 설정
API_KEY = "PKK8203BL2DHZ1KVANPZ"
API_SECRET = "idR8A4XCvIPpGoVWNMQqNy9dLkftbemheEI86Rg9"
BASE_URL = "https://paper-api.alpaca.markets"

api = tradeapi.REST(API_KEY, API_SECRET, BASE_URL)

# 나스닥 종목 가져오기
def get_nasdaq_symbols():
    assets = api.list_assets()
    return [asset.symbol for asset in assets if asset.exchange == "NASDAQ" and asset.tradable]

# yfinance로 주식 데이터 가져오기
def get_stock_data(symbol, period="6mo"):
    try:
        stock = yf.Ticker(symbol)
        data = stock.history(period=period)
        
        if data.empty:
            print(f"⚠ {symbol}은 상장폐지되었거나 데이터가 없습니다.")
            return None
        return data
    except Exception as e:
        print(f"⚠ {symbol} 데이터 가져오기 오류: {e}")
        time.sleep(60)  
        return None


# 이동평균선 (SMA) 계산
def get_sma(data, window=50):
    return data['Close'].rolling(window=window).mean()

# RSI 계산
def get_rsi(data, window=14):
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# 볼린저 밴드 계산
def get_bollinger_bands(data, window=20):
    sma = get_sma(data, window)
    std = data['Close'].rolling(window=window).std()
    upper_band = sma + (std * 2)
    lower_band = sma - (std * 2)
    return upper_band, lower_band

# 매수 전략: 이동평균선 교차, RSI, 볼린저 밴드
def check_buy_conditions(symbol):
    data = get_stock_data(symbol)

    if data is None or len(data) < 120:  # 120이평 이상을 계산하려면 최소 130일 데이터 필요
        print(f"⚠ {symbol} 데이터 부족으로 매수 조건 체크 건너뜀.")
        return False

    # 이동평균선 계산
    ma5 = get_sma(data, 5).iloc[-1]
    ma10 = get_sma(data, 10).iloc[-1]
    ma20 = get_sma(data, 20).iloc[-1]
    ma60 = get_sma(data, 60).iloc[-1]
    ma120 = get_sma(data, 120).iloc[-1]
    print(f"{ma5} {ma10} {ma20} {ma60} {ma120}")
    # RSI, 볼린저 밴드 추가 계산
    rsi = get_rsi(data)
    upper_band, lower_band = get_bollinger_bands(data)

    # 현재가
    price = data['Close'].iloc[-1]

    # ✅ 정배열 + RSI < 30 + 현재가 < 하단 볼린저 밴드
    #if (ma5 > ma10 > ma20 > ma60 > ma120) and rsi.iloc[-1] < 30 and price < lower_band.iloc[-1]:
    if (ma5 > ma10 > ma20 > ma60) and rsi.iloc[-1] < 30 and price < lower_band.iloc[-1]:
        print(f"{symbol} 매수 조건 만족! 가격: {price}")
        return True
    
    return False

# 매도 전략: 이동평균선 교차, RSI, 볼린저 밴드
def check_sell_conditions(symbol, buy_price):
    data = get_stock_data(symbol)
    sma_short = get_sma(data, 10)
    sma_long = get_sma(data, 50)
    rsi = get_rsi(data)
    upper_band, lower_band = get_bollinger_bands(data)

    # 매도 조건: 단기 이동평균선 < 장기 이동평균선, RSI > 70, 가격이 상단 볼린저 밴드 이상
    if sma_short.iloc[-1] < sma_long.iloc[-1] and rsi.iloc[-1] > 70 and data['Close'].iloc[-1] > upper_band.iloc[-1]:
        print(f"{symbol} 매도 조건 만족! 가격: {data['Close'].iloc[-1]}")
        return True
    # 손절 조건: 가격이 매수 가격의 5% 하락
    elif data['Close'].iloc[-1] <= buy_price * 0.95:
        print(f"{symbol} 손절 조건 만족! 가격: {data['Close'].iloc[-1]}")
        return True
    return False

# 보유 종목 조회
def get_positions():
    try:
        positions = api.list_positions()

        total_cost = 0
        total_profit = 0
        # 보유 종목 정보 출력 (한 줄로)
        for position in api.list_positions():
            print(f"보유 종목: {position.symbol} | 평균매수가: {position.avg_entry_price} | 현재가: {position.current_price} | 수량: {position.qty} | 수익: {position.unrealized_pl}")
            total_cost += float(position.avg_entry_price) * int(position.qty)
            # 총 수익 계산
            total_profit += float(position.unrealized_pl)

        # 전체 포지션 출력 후 총 매수가, 총 수익 출력
        print(f"총 매수가: ${total_cost:.2f} | 총 수익: ${total_profit:.2f}")

        return {p.symbol: {"buy_price": float(p.avg_entry_price), "quantity": int(p.qty)} for p in positions}
    except Exception as e:
        print(f"⚠ 보유 종목 조회 오류: {e}")
        return {}

# 알파카 API로 매수
def place_buy_order(symbol, qty):
    try:
        api.submit_order(
            symbol=symbol,
            qty=qty,
            side="buy",
            type="market",
            time_in_force="gtc"
        )
    except Exception as e:
        print(f"⚠ 매수 주문 실패: {e}")

# 알파카 API로 매도
def place_sell_order(symbol, qty):
    try:
        api.submit_order(
            symbol=symbol,
            qty=qty,
            side="sell",
            type="market",
            time_in_force="gtc"
        )
    except tradeapi.rest.APIError as e:
        # 공매도 불가 오류 처리
        if "cannot be sold short" in str(e):
            print(f"⚠ {symbol} 공매도 불가, 매도 실패")
        else:
            print(f"⚠ 매도 주문 실패: {e}")

# 매수/매도 트레이딩 로직
def trade_stock():
    nasdaq_symbols = get_nasdaq_symbols()  # 나스닥 종목 목록 가져오기
    positions = get_positions()  # 현재 보유 종목 가져오기

    # 매수 전략 실행
    for i, symbol in enumerate(nasdaq_symbols, start=1):

        # 100번째 마다 10초 대기
        if i % 100 == 0:
            print(f"⚠ 100번째 티커, 10초 대기...")
            time.sleep(10)

        # 이미 보유하고 있는 종목이면 매수 제외
        if symbol in positions:
            print(f"⚠ {symbol}은 이미 보유 중이므로 매수하지 않습니다.")
            continue  # 이미 보유한 종목은 매수하지 않음
        
        # 주식 데이터 가져오기
        stock_data = get_stock_data(symbol)
        if stock_data is None:
            print(f"⚠ {symbol} 데이터가 없어서 매수 조건 체크를 건너뜁니다.")
            continue  # 데이터가 없으면 건너뜀

        # 매수 조건 체크
        if check_buy_conditions(symbol) and symbol not in positions:
            print(f"{i}.{symbol} 매수 진행!")
            place_buy_order(symbol, 1)  # 예시로 1주 매수
        else:
            print(f"{i}.{symbol} 매수 조건 미충족.")

    # 매도 전략 실행 (보유 종목에 대해서만)
    for symbol, position in positions.items():
        buy_price = position['buy_price']
        qty = position['quantity']
        if check_sell_conditions(symbol, buy_price):
            print(f"{symbol} 매도 진행!")
            place_sell_order(symbol, qty)

# 자동매매 시작
trade_stock()
