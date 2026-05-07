# LightchangerT

LightchangerT é um controlador de LED consciente da rede para consoles de videogame. Ele detecta quando seus dispositivos de jogo (PlayStation, Xbox, Nintendo Switch, Steam Deck, etc.) estão online e altera a cor da sua fita de LED de acordo.

## Recursos
- **Suporte Multiplataforma**: Funciona no Raspberry Pi (Python) e ESP32 (C++).
- **Detecção de Deep Sleep**: Usa verificação de ping para garantir que os dispositivos estejam realmente acordados.
- **Lógica de Prioridade**: O último dispositivo a ficar online controla a cor do LED.
- **Configuração Web**: Interface web opcional integrada para gerenciar dispositivos e cores sem editar arquivos de configuração.
- **Cores Personalizáveis**: Mapeamento de cores RGB totalmente personalizável para cada marca.

## Plataformas Suportadas
- **Sony (PlayStation)**: Azul
- **Microsoft (Xbox)**: Verde
- **Nintendo (Switch)**: Vermelho
- **Steam**: Azul Claro
- **Nvidia (Shield)**: Verde Claro

## Instalação

### Python (Raspberry Pi / Linux)
1. Clone o repositório.
2. Instale as dependências: `pip install zeroconf` (opcional para mDNS).
3. Edite o `config.json` com suas configurações de rede.
4. Execute `python3 main.py`.

### ESP32
1. Abra o projeto no Arduino IDE ou PlatformIO.
2. Instale as dependências: **FastLED**, **ESPping**, **ESPAsyncWebServer**.
3. Edite o `config.h` com suas credenciais de WiFi.
4. Faça o upload para a sua placa ESP32.

## Configuração
Edite `config.json` (Python) ou `config.h` (ESP32) para:
- Alterar o Pino e a Quantidade de LEDs.
- Personalizar Cores.
- Definir IPs de Dispositivos Estáticos.
- Habilitar a Interface de Configuração Web.

## Configuração Web (Python)
Para habilitar a interface web, defina no `config.json`:
```json
"web_config_enabled": true,
"web_config_port": 80
```
Em seguida, reinicie a aplicação.

## Licença
MIT