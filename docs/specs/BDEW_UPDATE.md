# BDEW-Datenquellen Spezifikation

## Basisdaten

- **URL:** <https://bdew-codes.de/Codenumbers/BDEWCodes/GetCompanyList?jtStartIndex=1100&jtPageSize=50>
- **Payload:**

  ```text
  jtStartIndex=1100&jtPageSize=50
  ```

- **Response:**

  ```json
  {
    "Result": "OK",
    "Records": [
      {
        "Id": 59180,
        "CompanyUId": 667408,
        "Company": "Energy Revolt s.c."
      },
      {
        "Id": 882,
        "CompanyUId": 660780,
        "Company": "ENERGY TRADING COMPANY, j. s. a."
      },
      {
        "Id": 886,
        "CompanyUId": 660784,
        "Company": "Energy2day GmbH"
      },
      //...
      {
        "Id": 53663,
        "CompanyUId": 664869,
        "Company": "enplify eG"
      }
    ],
    "TotalRecordCount": 4408
  }
  ```

## Detaildaten

- **URL:** <https://bdew-codes.de/Codenumbers/BDEWCodes/GetBdewCodeListOfCompany?companyId=948&filter=>
- **Payload:**

  ```text
  companyId=948&filter=
  ```

- **Response:**

  ```json
  {
    "Result": "OK",
    "Records": [
      {
        "Id": 1544,
        "CompanyUId": 660846,
        "BdewCode": "9900179000009",
        "MarketFunctionName": "Netzbetreiber",
        "ContactName": "Hußenether, Johannes"
      },
      {
        "Id": 1545,
        "CompanyUId": 660846,
        "BdewCode": "9904709000009",
        "MarketFunctionName": "Messstellenbetreiber",
        "ContactName": "Pörnbacher, Dominic"
      },
      {
        "Id": 1547,
        "CompanyUId": 660846,
        "BdewCode": "9903080000001",
        "MarketFunctionName": "Lieferant",
        "ContactName": "Schaffer, Bianca"
      }
    ]
  }
  ```
