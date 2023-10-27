# ---- IMPORTANTE TENHA AS SEGUINTES BIBLIOTECAS DEVIDAMENTE INSTALADAS -----
# 
# PubSubClient
# ESP32Servo
# Buzzer
# PIR
#
# ----------------------------------------------------------------------------

# ESSE CODIGO FOI IMPLEMENTADO APENAS DE FORMA SIMULADA PELA PLATAFORMA WOKWI UTILIZANDO O MICROCONTROLADOR ESP32

# Importação dos módulos necessários
from machine import Pin, PWM
from umqtt.simple import MQTTClient
import network
import time
import _thread

# Configuração da rede WiFi
SSID = "Wokwi-GUEST"  # Nome da sua rede WiFi
PASSWORD = ""  # Senha da sua rede WiFi

# Configuração do MQTT
MQTT_BROKER = "test.mosquitto.org"  # Endereço do broker MQTT
TOPIC = b"/ThinkIOT/Servo-nodered"  # Tópico MQTT para subscrição

# Configuração do pino do servo
SERVO_PIN = 5  # Número do pino GPIO conectado ao servo

# Configuração do pino do botão e do buzzer
BUTTON_PIN = 14  # Número do pino GPIO conectado ao botão
BUZZER_PIN = 12  # Número do pino GPIO conectado ao buzzer

# Configuração dos pinos dos LEDs
LED_ALARM_ACTIVE_PIN = 23  # Número do pino GPIO do LED de alarme ativo
LED_ALARM_INACTIVE_PIN = 22  # Número do pino GPIO do LED de alarme inativo

# Adição da variável de controle para debounce
button_state = 0  # 0 indica que o botão está inativo, 1 indica que está ativo

# Inicializa o objeto do servo
servo = PWM(Pin(SERVO_PIN), freq=180)

# Inicializa o pino do botão e do buzzer
button = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_UP)  # Configura o pino do botão como entrada com pull-up
buzzer = PWM(Pin(BUZZER_PIN), freq=440, duty=0)  # Inicializa o buzzer

# Inicializa os pinos dos LEDs
led_alarm_active = Pin(LED_ALARM_ACTIVE_PIN, Pin.OUT)  # Configura o pino do LED ativo como saída
led_alarm_inactive = Pin(LED_ALARM_INACTIVE_PIN, Pin.OUT)  # Configura o pino do LED inativo como saída

# Inicializa a variável pir_active
pir_active = False  # Define uma variável para rastrear o estado do sensor PIR

# Inicializa o pino do sensor PIR
pir = Pin(15, Pin.IN)  # Configura o pino do sensor PIR como entrada

# Função de callback quando uma mensagem é recebida
def sub_cb(topic, msg):
    value = msg.decode()  # Converte a mensagem para string
    if value == "aberto":
        pos = 90
    elif value == "fechado":
        pos = 324
    else:
        pos = int(value)  # Caso a mensagem seja um valor numérico
    
    servo.duty(pos)  # Define a posição do servo
    print("Posição do servo ajustada para:", pos)

# Conecta-se à rede WiFi
def connect_wifi():
    sta_if = network.WLAN(network.STA_IF)  # Cria uma interface de rede WiFi
    sta_if.active(True)  # Ativa a interface WiFi
    sta_if.connect(SSID, PASSWORD)  # Conecta à rede WiFi
    while not sta_if.isconnected():
        pass
    print("Conectado à rede WiFi")
    print("Endereço IP:", sta_if.ifconfig()[0])  # Exibe o endereço IP

# Conecta-se ao broker MQTT
def connect_mqtt():
    global client  # Permite o acesso à variável 'client' fora desta função
    client = MQTTClient("ESPClient", MQTT_BROKER)  # Cria um cliente MQTT com um nome único
    client.set_callback(sub_cb)  # Define a função de callback para mensagens recebidas
    client.connect()  # Conecta-se ao broker MQTT
    client.subscribe(TOPIC)  # Subscreve ao tópico MQTT
    print("Conectado ao broker MQTT")

# Função para reconectar ao broker MQTT em caso de desconexão
def reconnect():
    while not client.is_connected():
        try:
            client.connect()
            client.subscribe(TOPIC)
        except Exception as e:
            print("Erro ao reconectar ao MQTT:", e)
            time.sleep(5)

# Função de inicialização do sensor PIR
def init_pir():
    pirstate = False  # Variável para rastrear o estado do sensor PIR

    while True:
        if pir_active:  # Verifica se o sensor PIR está ativo
            value = pir.value()  # Lê o valor do sensor PIR (1 para detecção, 0 para sem detecção)
            if value == 1:
                buzzer.duty(1023)  # Ligue o buzzer com potência máxima
                if not pirstate:
                    print("Movimento detectado!")
                    pirstate = True
            else:
                buzzer.duty(0)  # Desliga o buzzer
                if pirstate:
                    print("Movimento encerrado!")
                    pirstate = False
        time.sleep(0.1)

# Função para tratar o pressionamento do botão com debounce
def button_pressed(pin):
    global pir_active, button_state
    if button_state == 0:  # Verifica se o botão está no estado inativo
        button_state = 1  # Atualiza o estado do botão
        if pir_active:
            pir_active = False
            print("Sensor PIR desativado")
            buzzer.duty(0)
        else:
            pir_active = True
            print("Sensor PIR ativado")
            buzzer.duty(512)
        time.sleep(0.5)  # Aguarde 0.5 segundos antes de permitir outro clique
        button_state = 0  # Restaure o estado do botão

# Função de atualização dos LEDs
def update_leds():
    while True:
        if pir_active:
            led_alarm_active.on()  # Liga o LED de alarme ativo
            led_alarm_inactive.off()  # Desliga o LED de alarme inativo
        else:
            led_alarm_active.off()  # Desliga o LED de alarme ativo
            led_alarm_inactive.on()  # Liga o LED de alarme inativo
        time.sleep(0.1)

# Inicia as funções em threads separadas
_thread.start_new_thread(init_pir, ())  # Inicia a função de inicialização do sensor PIR em uma thread separada
_thread.start_new_thread(update_leds, ())  # Inicia a função de atualização dos LEDs em uma thread separada

# Inicialização
connect_wifi()  # Conecta-se à rede WiFi
connect_mqtt()  # Conecta-se ao broker MQTT

# Configura o tratador de interrupção para o botão
button.irq(trigger=Pin.IRQ_FALLING, handler=button_pressed)

# Loop principal
while True:
    try:
        client.wait_msg()  # Espera por mensagens do broker MQTT
    except Exception as e:
        print("Erro no loop principal:", e)
        reconnect()  # Reconecta-se em caso de erro