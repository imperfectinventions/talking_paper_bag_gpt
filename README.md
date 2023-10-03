# Talking Paper Bag GPT
# Table of Contents
- [Introduction](#introduction)
- [Requirements](#requirements)
   - [Bill of Materials](#bill-of-materials)
   - [Tools Needed](#tools-needed)
- [Assembly](#assembly)
   - [Print Settings](#print-settings)
   - [Part Assembly](#part-assembly)
   - [Electrical Wiring](#electrical-wiring)
- [Software Setup](#software-setup)
   - [Settings File](#settings-file)
   - [Included System Messages](#included-system-messages)

## Introduction

This device turns any paper bag into a talking puppet! It uses OpenAI's GPT3.5 turbo as well as the Azure Speech service in order to enable communication with this paper bag.

You can also give the paper bag a personality via specifying the system message. I have a few pre-built personalities that you can use (a lot of them are problematic, though so heads up).

## Requirements

### Bill of Materials

|  Name                  | Purpose           | Amazon Link    |
|------------------------|-------------------|----------------|
| 1 Libre AML-S905X-CC   | The Brains of the system. Can run linux. Future updates may involve using MicroPython and remove the need for an OS, but this is the current design. Also has 4 USB ports, so it was easy to run USB peripherals on them. | [link](https://www.amazon.com/gp/product/B074P6BNGZ/ref=ppx_yo_dt_b_search_asin_title?ie=UTF8&th=1) |
| 1 Wifi Dongle          | WiFi connectivity. This board does have an Ethernet plug so you can use that and free up a USB port. I just went with this. | [link](https://www.amazon.com/gp/product/B0BNFKJPXS/ref=ppx_yo_dt_b_search_asin_title?ie=UTF8&psc=1) |
| Some Stranded Wire     | To connect everything together | [Link to the Wire I Used](https://www.amazon.com/gp/product/B077HQ779B/ref=ppx_yo_dt_b_search_asin_title?ie=UTF8&psc=1) |
| Crimp Connectors       | To make the wire connections. You could bring your own pre-made wires for this, but I just decided at one point it was cheaper to make my own. | [Link with Crimper](https://www.amazon.com/gp/product/B07VQ6YNSC/ref=ppx_yo_dt_b_search_asin_title?ie=UTF8&psc=1) |
| 1 SG90 Servo           | To move the paper bag head. | [Link](https://www.amazon.com/gp/product/B07Q6JGWNV/ref=ppx_yo_dt_b_search_asin_title?ie=UTF8&psc=1) |
| Hot Glue               | For glueing things together when needed | [Link](https://www.amazon.com/AdTech-Glue-Sticks-Full-Clear/dp/B000PCY91O/ref=sr_1_4?keywords=glue+gun+sticks) |
| M3 Screws of Various Sizes | For securing all of the 3D printed parts together | [Link](https://www.amazon.com/gp/product/B08H24W42K/ref=ppx_yo_dt_b_search_asin_title?ie=UTF8&psc=1) |
| A USB Speaker          | For hearing ChatGPT talk to you. Could go with a combined speaker/microphone.  | [Link](https://www.amazon.com/gp/product/B08QRYTPGH/ref=ppx_yo_dt_b_search_asin_title?ie=UTF8&psc=1) |
| A USB Microphone       | For talking to ChatGPT. Could go with a combined speaker/mic. Similar to the one I used. | [Link](https://www.amazon.com/Cyber-Acoustics-Premium-Condenser-Microphone/dp/B0857HD2PT/ref=sr_1_31?keywords=usb+microphone+insignia) |
| PLA Filament           | For making the full 3D-printed assembly. | [Link](https://www.amazon.com/gp/product/B08QN5FQX7/ref=ppx_yo_dt_b_search_asin_title?ie=UTF8&psc=1) |
| Some solid core wire   | For the button | [Link](https://www.amazon.com/gp/product/B081GMJVPB/ref=ppx_yo_dt_b_search_asin_title?ie=UTF8&psc=1) |
| A Push Button          | For controlling when to talk to the Paper Bag | [Link](https://www.amazon.com/gp/product/B09R47N37H/ref=ppx_yo_dt_b_search_asin_title?ie=UTF8&psc=1) |
| Paper Bags | For the whole aesthetic |  | 
| Paper Bag Decorations | For decorations |  |

### Tools Needed

|  Name                  | Purpose           | Amazon Link    |
|------------------------|-------------------|----------------|
| Wire Stripper          | Stripping Wires   | [Link](https://www.amazon.com/gp/product/B09539R6TD/ref=ppx_yo_dt_b_search_asin_title?ie=UTF8&psc=1) |
| 3D Printer             | For printing the full 3D printer assembly | [I use a modded Geeetech A10, but link to some random printer](https://www.amazon.com/Comgrow-Creality-Ender-Aluminum-220x220x250mm/dp/B07BR3F9N6/ref=sr_1_11?keywords=geeetech+a10&ufe=app_do%3Aamzn1.fos.18ed3cb5-28d5-4975-8bc7-93deae8f9840) | 
| Soldering Iron         | For soldering | [Link to Default Soldering Iron, not sponsored](https://www.amazon.com/Soldering-Digital-Welding-Portable-Electric/dp/B08R3515SF/ref=sr_1_5?keywords=soldering+iron) |
| Hot Glue Gun           | For some touch up jobs, securing wires in place, etc. | |

## Assembly

### Print Settings

### Part Assembly

### Electrical Wiring

## Software Setup

### Settings File

### Included System Messages

