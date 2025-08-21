# Specifications for WebUI

This is a WebUI for administrative Tasks on the Application and it's Database

## General

The WebUI is based on FastAPI and a so called admin interface.
It provides a user-friendly way to manage and interact with the application's database.

## Main funtionality

- User Authentication is not needed, since the credentials for all related parts reside
  in the .env file of the main repository, which should be used for that purpose.
- Different views of the company table for the purpose of:
  - Displaying all companies based on BDEW and show the entries for BNetzA and the alternatives.
    The BNetzA-Entry shall be editable. Also the alternative matches should be editable.
    It should be possible to mark and unmark entries as `manual_verification`
  - Displaying all companies based on BDEW and display the basic VNBdigital data
  - Select a BDEW company from the list using a dropdown and display all VNBdigital data.
    This shall include a OpenStreetMaps view of the GEOJSON data.
