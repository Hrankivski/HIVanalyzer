# Офіційний образ Python 3.11 (бо нові версії numpy вимагають >= 3.11)
FROM python:3.11-slim

# Встановлення необхідних системних утиліт та бібліотек
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    libgomp1 \
    libexpat1 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Встановлення EnergyPlus 25.2.0
ENV EPLUS_VERSION=25.2.0
ENV EPLUS_DL_URL=https://github.com/NREL/EnergyPlus/releases/download/v25.2.0/EnergyPlus-25.2.0-cf7368216c-Linux-Ubuntu22.04-x86_64.tar.gz

RUN wget -qO /tmp/energyplus.tar.gz $EPLUS_DL_URL && \
    tar -xzf /tmp/energyplus.tar.gz -C /usr/local/ && \
    mv /usr/local/EnergyPlus* /usr/local/EnergyPlus && \
    rm /tmp/energyplus.tar.gz

# Вказуємо шлях до EnergyPlus для Python коду
ENV EPLUS_EXE=/usr/local/EnergyPlus/energyplus

WORKDIR /app

# Спочатку копіюємо requirements для кешування шару Docker
COPY requirements.txt .

# Встановлюємо CPU-версію PyTorch
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Встановлюємо інші залежності
RUN pip install --no-cache-dir -r requirements.txt

# Копіюємо весь код
COPY . .

# Порт Streamlit
EXPOSE 8501

ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

# Команда запуску
CMD ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]
