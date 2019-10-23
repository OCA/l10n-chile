To use this module, you need to:

1) Go to https://api.sbif.cl/api/contactanos.jsp and ask for a token (option: "obtener una api key").
2) When you receive the API token in your email, go to technical/parameters and declare its value using the following key:
"sbif.financial.indicators.apikey" (replace "PUT_HERE_YOUR_SBIF_TOKEN")
3) Be sure to go to technical/scheduled actions and check the hour of connection at "Update Chilean Financial Indicators"
It is recommended that the time of connection be made between 9am and 10pm to get the daily value of rates. (Earlier, they could not be available).



