# Nest NodeServer for Polyglot v2

(c) Einstein.42 aka James Milne.  
MIT license.

### Requirements

Install via the NodeServer Store or clone the repository and run the install.sh script.

#### Install Guide

The Nest NodeServer now uses the official API from Nest/Google. So it was moved to a Oauth2/token
authentication mechanism.

When you run it the first time, check the log from Dashboard > Nest NodeServer > Details > Log and go to the URL that is provided. This will request that you allow '3C Solutions' access to your Nest data. It's just giving access to your running NodeServer. No one else will have access to any data what-so-ever.

Once you click accept and login, you will get a PIN number. That PIN number then needs to be added to the Custom Parameters section of the NodeServer in the Polyglot Frontend under Dashboard > Nest NodeServer > Details > Custom Parameters. Creat a key name 'pin' and paste the PIN provided to the value field. Hit save, then restart the NodeServer.

Once the NodeServer is restarted, your Thermostats will pop into ISY and away you go. Please pay attention to the notes section below.

I plan on implementing the new REST streaming mechanism that Nest uses for reads at some point as well, but for now this should work well.

The External Temperature API was deprecated and is no longer supported by Nest, so I had to remove it.

[See Here for the UDI Forum](https://forum.universal-devices.com/topic/23143-polyglot-v2-nest-nodeserver/)

[And here for a Visual Walkthrough](https://imgur.com/a/IUWfV)


# Notes
The Nest Polyglot polls the Nest API every 30 seconds due to Nest anti-flooding mechanisms that
temporarily disable queries to the API. So if anything is updated outside of ISY it could take
up to 30 seconds to be reflected in the ISY interface.

Nest only updates the structure api every 600 seconds (5 minutes). This only affects AWAY state
so if your device is set away or returned from away it will take up to 5 minutes to reflect in
your ISY node.
