import os

st.write("Current files:", os.listdir())

df = pd.read_csv("Sports-ai-bets/bet_log.csv")
