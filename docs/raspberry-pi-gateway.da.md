# Billig Raspberry Pi RS485-gateway

Denne guide beskriver en lille, automatisk og read-only RS485-til-Ethernet-gateway til Dantherm HCH5 MK1. Den er afprøvet på en Raspberry Pi 2 Model B med en FTDI-baseret USB-RS485-adapter. Home Assistant forbinder til gatewayens rå TCP-port gennem Dantherm HCH PassiveLink.

Gatewayen er ikke en Modbus-master. Den sender ingen forespørgsler eller kommandoer til anlægget, men videresender kun de bytes, som allerede findes på RS485-bussen. Dantherms eksisterende styring fortsætter derfor uændret.

> **Uofficielt community-projekt:** Løsningen er ikke udviklet, leveret, godkendt, certificeret eller supporteret af Dantherm Group. Arbejde på ventilationsanlæggets kabling sker på eget ansvar. Afbryd strømmen før kablingen ændres, og brug en autoriseret installatør, hvis terminalernes funktion er uklar.

## Dele

- Raspberry Pi 2 Model B eller nyere
- microSD-kort på mindst 8 GB
- stabil 5 V-strømforsyning passende til Pi-modellen
- Ethernet-kabel
- USB-RS485-adapter med Linux-understøttelse
- snoet lederpar, eksempelvis 2 × 0,35 mm², til RS485 A/B

Referenceinstallationen bruger denne type [Joy-It USB-RS485-adapter fra Conrad](https://www.conradelektronik.dk/da/p/joy-it-omformer-usb-rs485-raspberry-pi-arduino-1x-usb-2-0-stik-a-1x-2-traads-ledning-sort-2149078.html). Den konkrete adapter i testen identificeres af Linux som FTDI FT232R (`0403:6001`). Produktrevisioner kan ændre chipset, så kontrollér altid resultatet af `lsusb`. Andre adaptere kan bruges, hvis de understøtter `19200 8E1`, automatisk senderetning og Linux. En galvanisk isoleret adapter anbefales til en permanent installation.

## Topologi og kabling

Lad den eksisterende forbindelse mellem Dantherm-styringerne være intakt. Gatewayen forbindes parallelt som et kort, passivt lyttepunkt:

```text
Eksisterende Dantherm RS485 A ─────────────── A på USB-RS485
Eksisterende Dantherm RS485 B ─────────────── B på USB-RS485
                                                │ USB
                                         Raspberry Pi
                                                │ Ethernet
                                         Home Assistant
```

Brug et snoet par og hold det væk fra 230/400 V, motor- og kontaktorledninger. Tre meter er uproblematisk ved den anvendte hastighed. Farverne er valgfrie, men brug samme farve til samme signal i begge ender.

Producenter navngiver ikke altid A og B ens. Hvis der ikke registreres trafik, afbryd strømmen og byt A/B i kun den ene ende. Slå adapterens ekstra 120 Ω-terminering fra, medmindre den eksisterende bustopologi udtrykkeligt kræver den. Tilslut aldrig beskyttelsesjord eller en strømleder som RS485-GND.

Se også [det generelle forbindelsesdiagram](rs485-wiring.svg).

## 1. Installér Raspberry Pi OS

Brug Raspberry Pi Imager og vælg:

- **Raspberry Pi OS Lite (32-bit)**
- hostname, eksempelvis `danthermhch5`
- en ny bruger og en stærk adgangskode
- SSH aktiveret
- korrekt tidszone

Desktopmiljø er ikke nødvendigt. Tilslut Pi'en med Ethernet og start den. Find dens midlertidige IP-adresse i routeren og log ind:

```bash
ssh DIN_BRUGER@PIENS_IP
```

Opdatér operativsystemet:

```bash
sudo apt update
sudo apt full-upgrade -y
sudo apt install -y curl git python3 python3-venv python3-pip
sudo reboot
```

## 2. Giv Pi'en en fast IP-adresse

Det anbefales først at lave en DHCP-reservation i routeren. Alternativt kan Raspberry Pi OS Bookworm konfigureres med NetworkManager.

Find forbindelsesnavnet:

```bash
nmcli connection show
```

Eksempel med IP `10.0.0.12/24`, router `10.0.0.1` og DNS `10.0.0.1`:

```bash
sudo nmcli connection modify "Wired connection 1" \
  ipv4.method manual \
  ipv4.addresses 10.0.0.12/24 \
  ipv4.gateway 10.0.0.1 \
  ipv4.dns 10.0.0.1
sudo nmcli connection up "Wired connection 1"
```

Tilpas forbindelsesnavn, adresse, gateway og DNS til dit netværk. Kontrollér derefter:

```bash
ip address show eth0
ip route
ping -c 3 10.0.0.1
```

## 3. Find USB-RS485-adapteren

Sæt adapteren i Pi'en og kør:

```bash
lsusb
ls -l /dev/serial/by-id/
```

Brug altid stien under `/dev/serial/by-id/` i stedet for `/dev/ttyUSB0`, fordi nummeret kan ændre sig efter en genstart. Eksempel:

```text
/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_A5069RR4-if00-port0
```

Kopiér din egen sti; eksemplet må ikke anvendes ukritisk.

## 4. Installér gatewayprogrammet

Opret en begrænset systembruger og programmappe:

```bash
sudo useradd --system --home /opt/dantherm-passivelink \
  --shell /usr/sbin/nologin --groups dialout passivelink
sudo install -d -o passivelink -g passivelink /opt/dantherm-passivelink
```

Hent programmet og opret et isoleret Python-miljø:

```bash
sudo curl -fsSL \
  https://raw.githubusercontent.com/MRDonnii/dantherm-hch-passivelink/main/gateway/passivelink_gateway.py \
  -o /opt/dantherm-passivelink/passivelink_gateway.py
sudo chown passivelink:passivelink /opt/dantherm-passivelink/passivelink_gateway.py
sudo -u passivelink python3 -m venv /opt/dantherm-passivelink/venv
sudo -u passivelink /opt/dantherm-passivelink/venv/bin/pip install --upgrade pip
sudo -u passivelink /opt/dantherm-passivelink/venv/bin/pip install pyserial==3.5
```

## 5. Installér systemd-tjenesten

Hent servicefilen:

```bash
sudo curl -fsSL \
  https://raw.githubusercontent.com/MRDonnii/dantherm-hch-passivelink/main/gateway/dantherm-passivelink.service \
  -o /etc/systemd/system/dantherm-passivelink.service
```

Åbn den:

```bash
sudo nano /etc/systemd/system/dantherm-passivelink.service
```

Erstat denne tekst i `ExecStart`:

```text
/dev/serial/by-id/REPLACE_WITH_YOUR_ADAPTER
```

med adapterstien fra trin 3. Gem med `Ctrl+O`, Enter og `Ctrl+X`.

Kontrollér servicefilen, aktivér den ved opstart og start den:

```bash
sudo systemd-analyze verify /etc/systemd/system/dantherm-passivelink.service
sudo systemctl daemon-reload
sudo systemctl enable --now dantherm-passivelink.service
sudo systemctl status dantherm-passivelink.service --no-pager
```

Se live-loggen:

```bash
journalctl -u dantherm-passivelink.service -f
```

Når A/B er korrekt tilsluttet, viser loggen, at adapteren er åbnet på `19200 8E1`. TCP-porten kontrolleres med:

```bash
ss -lntp | grep 4196
```

## 6. Aktivér hardware-watchdog

Raspberry Piens hardware-watchdog kan genstarte maskinen, hvis operativsystemet låser helt.

```bash
echo 'dtparam=watchdog=on' | sudo tee -a /boot/firmware/config.txt
sudo mkdir -p /etc/systemd/system.conf.d
sudo nano /etc/systemd/system.conf.d/watchdog.conf
```

Indsæt:

```ini
[Manager]
RuntimeWatchdogSec=30s
RebootWatchdogSec=2min
```

Gem og genstart:

```bash
sudo systemctl daemon-reexec
sudo reboot
```

Efter genstart:

```bash
systemctl show --property=RuntimeWatchdogUSec
systemctl is-enabled dantherm-passivelink.service
systemctl is-active dantherm-passivelink.service
```

Tjenesten starter automatisk efter strømbrud og prøver igen hvert tredje sekund, hvis USB-adapteren fjernes eller kommer tilbage. TCP-klienter, der forsøger at sende data, bliver afbrudt.

## 7. Åbn kun porten på lokalnettet

Hvis `ufw` er aktiveret, tillad kun Home Assistant-maskinen. Eksempel hvor Home Assistant har `10.0.0.25`:

```bash
sudo ufw allow from 10.0.0.25 to any port 4196 proto tcp
```

Eksponér aldrig port 4196 mod internettet. Brug ikke port-forwarding.

## 8. Tilføj gatewayen i Home Assistant

1. Installér **Dantherm HCH PassiveLink** gennem HACS.
2. Genstart Home Assistant.
3. Åbn **Indstillinger → Enheder og tjenester → Tilføj integration**.
4. Vælg **Dantherm HCH PassiveLink**.
5. Vælg **RS485 over TCP**.
6. Indtast Pi'ens faste IP, eksempelvis `10.0.0.12`.
7. Indtast port `4196`.

IP, port og forbindelsestype kan senere ændres via integrationens **Konfigurér**-knap uden at slette entiteterne.

## Test efter installation

På Pi'en:

```bash
systemctl is-active dantherm-passivelink.service
journalctl -u dantherm-passivelink.service --since "10 minutes ago" --no-pager
ss -ntp | grep 4196
```

Når Home Assistant er forbundet, skal `ss` vise en etableret forbindelse fra Home Assistant til Pi'ens port 4196. I Home Assistant skal **RS485-bustrafik** blive aktiv, og temperaturerne skal begynde at opdatere.

Test også genstart og genforbindelse:

```bash
sudo reboot
```

Kontrollér efter opstart, at tjenesten er aktiv igen. Fjern kun USB-adapteren som test, når det kan gøres sikkert; tjenesten skal fortsætte med at prøve og automatisk åbne adapteren igen, når den sættes tilbage.

## Fejlfinding

### Ingen RS485-trafik

- kontrollér, at adapteren findes under `/dev/serial/by-id/`;
- kontrollér, at servicefilen bruger præcis den sti;
- kontrollér A/B og byt dem i kun én ende, hvis nødvendigt;
- kontrollér `19200 8E1`;
- slå ekstra 120 Ω-terminering fra;
- kontrollér, at den eksisterende Dantherm-styring stadig kommunikerer.

### Permission denied på USB-porten

```bash
groups passivelink
ls -l /dev/serial/by-id/
sudo usermod -aG dialout passivelink
sudo systemctl restart dantherm-passivelink.service
```

### Home Assistant kan ikke forbinde

```bash
ping -c 3 HOME_ASSISTANT_IP
ss -lntp | grep 4196
sudo ufw status
```

Kontrollér også, at Home Assistant bruger Pi'ens aktuelle IP og port 4196.

### Se de seneste fejl

```bash
journalctl -u dantherm-passivelink.service -n 100 --no-pager
```

## Opdater gatewayprogrammet

```bash
sudo systemctl stop dantherm-passivelink.service
sudo curl -fsSL \
  https://raw.githubusercontent.com/MRDonnii/dantherm-hch-passivelink/main/gateway/passivelink_gateway.py \
  -o /opt/dantherm-passivelink/passivelink_gateway.py
sudo chown passivelink:passivelink /opt/dantherm-passivelink/passivelink_gateway.py
sudo systemctl start dantherm-passivelink.service
sudo systemctl status dantherm-passivelink.service --no-pager
```

## Begrænsninger

- Gatewayen er kun til aflæsning.
- Den overtager ikke styringen fra HRC/HAC1.
- Den almindelige passive strøm indeholder ikke nødvendigvis alle setpoints hele tiden.
- Registerfortolkningen er baseret på observeret trafik fra HCH5 MK1 + HAC1.
- Løsningen er ikke beregnet til HCH5 MKII eller nyere UVC-baserede anlæg.
# Valgfri udvidelse: to temperaturfølere på vandforvarmen

Denne del er helt valgfri. RS485-broen og Dantherm-integrationen virker uden
følerne. Følerservicen kører som en selvstændig systemd-tjeneste på port 4197.
Hvis en føler mangler, tjenesten stopper eller Pi'en ikke kan nås, bliver kun
vandforvarmens egne entiteter utilgængelige. Dantherm-data på port 4196
fortsætter uændret.

Der bruges to vandtætte DS18B20-følere: én på fremløbet og én på returen. Begge
tilsluttes parallelt til Raspberry Pi'ens 1-Wire-bus:

| DS18B20 | Raspberry Pi 2B |
| --- | --- |
| VCC | Pin 1, 3,3 V |
| Data | Pin 7, GPIO4 |
| GND | Pin 6, GND |

Sæt en 4,7 kΩ modstand mellem Data/GPIO4 og 3,3 V. Brug ikke 5 V på GPIO4.
Kontrollér altid lederfarverne i følerens datablad; farver er ikke en sikker
standard. Montér følerne med god termisk kontakt og isolér dem udvendigt.

Aktivér 1-Wire permanent:

```bash
echo 'dtoverlay=w1-gpio,gpiopin=4' | sudo tee -a /boot/firmware/config.txt
sudo reboot
```

Efter genstart vises følernes unikke adresser således:

```bash
ls -1 /sys/bus/w1/devices/28-*
```

Installér den separate HTTP-tjeneste fra projektmappen:

```bash
sudo useradd --system --home /opt/dantherm-passivelink --shell /usr/sbin/nologin passivelink 2>/dev/null || true
sudo install -d -o passivelink -g passivelink /opt/dantherm-passivelink
sudo install -d -o root -g passivelink -m 0750 /etc/dantherm-passivelink
sudo install -o passivelink -g passivelink -m 0755 gateway/onewire_temperature_server.py /opt/dantherm-passivelink/
sudo install -o root -g root -m 0644 gateway/dantherm-passivelink-onewire.service /etc/systemd/system/
sudo cp gateway/onewire.example.json /etc/dantherm-passivelink/onewire.json
sudo chown root:passivelink /etc/dantherm-passivelink/onewire.json
sudo chmod 0640 /etc/dantherm-passivelink/onewire.json
```

Tjenesten finder automatisk to tilsluttede DS18B20-følere. Adresser kan stadig
låses i `/etc/dantherm-passivelink/onewire.json`, men hvis de gemte adresser
ikke findes, bruges de to fundne følere automatisk. Start derefter:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now dantherm-passivelink-onewire.service
curl http://127.0.0.1:4197/temperatures
```

Et normalt svar indeholder `available: true` og begge temperaturer. I Home
Assistant åbnes **Indstillinger → Enheder og tjenester → Dantherm HCH
PassiveLink → Konfigurer**. Aktivér de valgfrie vandforvarmefølere, angiv Pi'ens
IP-adresse og port `4197`. Der oprettes en særskilt enhed med fremtemperatur,
returtemperatur, delta-T, varmeoverførsel og forbindelsesstatus. Hvis frem og
retur vises omvendt, aktivér **Byt frem- og returføler** i samme indstillinger;
det kræver ingen ændring på Pi'en.

Delta-T viser, at vandkredsen faktisk overfører varme, men er ikke en måling i
kW. En rigtig effektberegning kræver desuden en kalibreret måling af vandflowet.
