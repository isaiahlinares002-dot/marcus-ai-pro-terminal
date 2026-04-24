import pandas as pd

def get_assets():
    sp500 = pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")[0]["Symbol"].tolist()[:50]
    nasdaq = pd.read_html("https://en.wikipedia.org/wiki/NASDAQ-100")[4]["Ticker"].tolist()[:50]

    penny = [
        "SNDL","BBIG","ATER","MULN","IDEX","NAKD","GNUS","NOK",
        "AMC","GPRO","FUBO","PLUG","SOFI","RIOT","MARA","CLNE",
        "WISH","OPEN","SKLZ","HUT","BITF","CLOV","WKHS","BB",
        "TLRY","CGC","APRN","RIDE","NKLA","GOEV","SPCE","LCID",
        "XELA","CTRM","ZOM","OCGN","NAOV","BIOL","SENS","BNGO",
        "MARK","VISL","EVFM","ENG","FRSX","KOSS","HCMC","AEZS"
    ]

    crypto = [
        "BTC-USD","ETH-USD","XRP-USD","DOGE-USD","ADA-USD","SOL-USD"
    ]

    all_assets = list(set(sp500 + nasdaq + penny + crypto))
    return [s.replace(".", "-") for s in all_assets]