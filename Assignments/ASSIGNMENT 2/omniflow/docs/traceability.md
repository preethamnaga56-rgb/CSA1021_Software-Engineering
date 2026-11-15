# Traceability matrix: Requirement -> UML element -> Component -> Validation scenario

| Requirement | UML | Component | Scenario |
|---|---|---|---|
| FR-01 | UC15; User | Identity & Access | S6 |
| FR-02 | UC15; User; UC08 | Identity & Access | S6 |
| FR-03 | UC01; Order; OrderLine; SEQ1 | Order & Checkout | S8; X3 |
| FR-04 | UC01; Order; RegionalPolicy | Order & Checkout; Regional Policy | S8 |
| FR-05 | UC01; StockItem; Reservation | Stock & Reservation; PostgreSQL | S1 |
| FR-06 | Reservation; STM1 | Stock & Reservation | S7 |
| FR-07 | UC03; PaymentEvent; SEQ1 | Payment Callback; PostgreSQL | S2; S8 |
| FR-08 | UC03; STM1; RefundRequest | Payment Callback; Refund Approval | S7 |
| FR-09 | STM1; Order | Order & Checkout; Fulfilment & Tracking | S4 |
| FR-10 | UC04; Order | Fulfilment & Tracking | S4 |
| FR-11 | UC05; STM1; StockItem | Fulfilment & Tracking; Stock & Reservation | S4 |
| FR-12 | UC12; IntegrationIntent; SEQ1 | Integration Worker; PostgreSQL | S5 |
| FR-13 | UC02; Order | Order & Checkout | S6 |
| FR-14 | UC06; Order; RefundRequest | Order & Checkout; Identity & Access | S6 |
| FR-15 | UC07; RefundRequest; STM2 | Refund Approval | S3 |
| FR-16 | UC08; RefundRequest; STM2; RegionalPolicy | Refund Approval; Identity & Access | S6; X2 |
| FR-17 | UC09; STM2; SEQ2; RefundRequest | Refund Approval; Integration Worker | S3 |
| FR-18 | AuditEvent | PostgreSQL | S2 |
| FR-19 | UC10 | Reporting | X5 |
| FR-20 | UC11; RegionalPolicy | Regional Policy | X2 |
| FR-21 | UC13; ScanEvent; SEQ3 | Scan Ingest | X1 |
| FR-22 | UC13; ScanEvent; SEQ3 | Scan Ingest; PostgreSQL | X1 |
| FR-23 | UC14; ScanEvent; StockItem | Scan Ingest; Stock & Reservation | X4 |
| FR-24 | UC08; SEQ3; STM2 | Refund Approval; Identity & Access | X2 |
| FR-25 | ScanEvent | Scan Ingest | X4 |
| NFR-01 | UC01 | Order & Checkout; PostgreSQL | P1 |
| NFR-02 | UC01; UC03; StockItem; PaymentEvent | Stock & Reservation; Payment Callback; PostgreSQL | S1; S2; P6 |
| NFR-03 | SEQ1; IntegrationIntent | Integration Worker; Payment Callback | S5 |
| NFR-04 |  | PostgreSQL | P2 |
| NFR-05 | UC15; UC03 | Identity & Access; Payment Callback | S6; S8 |
| NFR-06 | UC02; UC06 | Order & Checkout | P3 |
| NFR-07 |  | PostgreSQL | P7 |
| NFR-08 | UC06 | Order & Checkout; Fulfilment & Tracking | S6 |
| NFR-09 | UC13; UC01 | Scan Ingest; Order & Checkout; Reporting | X1; X3; P4 |
| NFR-10 | UC10 | Reporting | X5; P5 |
