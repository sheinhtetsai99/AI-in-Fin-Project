--
-- PostgreSQL database dump
--

-- Dumped from database version 17.0
-- Dumped by pg_dump version 17.0

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

DROP DATABASE sampledb;
--
-- Name: sampledb; Type: DATABASE; Schema: -; Owner: postgres
--

CREATE DATABASE sampledb WITH TEMPLATE = template0 ENCODING = 'UTF8';


ALTER DATABASE sampledb OWNER TO postgres;

\connect sampledb

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: transactions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.transactions (
    transaction_id integer NOT NULL,
    username character varying(100),
    transaction_date timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    description character varying(255),
    amount numeric(10,2),
    transaction_type character varying(20),
    balance_after numeric(10,2),
    merchant_category_code character varying(4),
    location character varying(255),
    ip_address character varying(45),
    device_id character varying(255),
    transaction_method character varying(50),
    status character varying(20) DEFAULT 'completed'::character varying,
    risk_score numeric(5,2),
    fraud_flag boolean DEFAULT false,
    merchant_name character varying(255),
    currency character varying(3) DEFAULT 'USD'::character varying,
    geographic_location point,
    user_agent character varying(500),
    ai_reasoning text,
    ai_flags jsonb,
    CONSTRAINT transactions_transaction_type_check CHECK (((transaction_type)::text = ANY ((ARRAY['credit'::character varying, 'debit'::character varying])::text[])))
);


ALTER TABLE public.transactions OWNER TO postgres;

--
-- Name: transactions_transaction_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.transactions_transaction_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.transactions_transaction_id_seq OWNER TO postgres;

--
-- Name: transactions_transaction_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.transactions_transaction_id_seq OWNED BY public.transactions.transaction_id;


--
-- Name: useraccount; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.useraccount (
    id integer NOT NULL,
    username character varying(100) NOT NULL,
    password character varying(300) NOT NULL
);


ALTER TABLE public.useraccount OWNER TO postgres;

--
-- Name: useraccount_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.useraccount_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.useraccount_id_seq OWNER TO postgres;

--
-- Name: useraccount_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.useraccount_id_seq OWNED BY public.useraccount.id;


--
-- Name: transactions transaction_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.transactions ALTER COLUMN transaction_id SET DEFAULT nextval('public.transactions_transaction_id_seq'::regclass);


--
-- Name: useraccount id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.useraccount ALTER COLUMN id SET DEFAULT nextval('public.useraccount_id_seq'::regclass);


--
-- Data for Name: transactions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.transactions (transaction_id, username, transaction_date, description, amount, transaction_type, balance_after, merchant_category_code, location, ip_address, device_id, transaction_method, status, risk_score, fraud_flag, merchant_name, currency, geographic_location, user_agent, ai_reasoning, ai_flags) FROM stdin;
6	testaccount2	2024-10-28 14:50:23.072859	Unknown Transaction	-300.00	debit	7708.19	\N	Russia	192.168.1.1	device_123	wire_transfer	flagged	95.00	f	Unknown	USD	\N	\N	This transaction poses a very high risk of fraud due to the location being in Russia, an unknown merchant, a wire transfer method which is unusual for the account holder, and the device and IP being different from the usual patterns.	["Location Risk", "Amount Risk", "Method Risk", "Pattern Risk"]
2	testaccount2	2024-10-27 13:52:37.809482	Grocery Shopping	-156.32	debit	4843.68	5411	Boston, MA	192.168.1.2	device_123	card_present	suspicious	61.00	f	Whole Foods	USD	\N	\N	This transaction poses a high risk due to the location being outside the NYC metro area, the amount being relatively high for a typical Whole Foods purchase, and the card-present method used in an unfamiliar location.	["Location Risk", "Amount Risk", "Method Risk"]
1	testaccount2	2024-10-27 13:52:37.809482	Initial Deposit	5000.00	credit	5000.00	6011	New York, NY	192.168.1.1	device_123	online	flagged	81.00	f	Bank Transfer	USD	\N	\N	The transaction amount of $5000.0 is unusually high for a bank transfer within the NYC area. The online method, along with the device and IP address being used for the first time, raises significant concerns.	["Amount Risk", "Method Risk", "Pattern Risk"]
5	testaccount2	2024-10-27 13:52:37.809482	Restaurant Payment	-89.99	debit	8008.19	5812	Las Vegas, NV	192.168.1.4	device_456	card_present	flagged	85.00	f	Casino Restaurant	USD	\N	\N	This transaction poses a very high risk of potential fraud due to multiple concerning factors.	["Location Risk", "Amount Risk", "Method Risk"]
3	testaccount2	2024-10-27 13:52:37.809482	Salary Deposit	3500.00	credit	8343.68	6011	New York, NY	192.168.1.1	device_123	wire_transfer	flagged	85.00	f	ACME Corp	USD	\N	\N	The transaction poses a high risk due to the high amount for a wire transfer in NYC, which is unusual. Additionally, the device ID and IP address associated with the transaction are not recognized in previous patterns.	["Amount Risk", "Method Risk", "Pattern Risk"]
12	testaccount2	2024-11-12 23:42:59.402978	ATM Withdrawal	-1000.00	debit	10218.19	\N	Dubai, UAE	192.168.1.1	device_123	unusual_terminal	flagged	95.00	f	Unknown Merchant	USD	\N	\N	The transaction is high-risk due to the substantial amount, location in Dubai, UAE, and the unknown merchant. International transactions should be scrutinized, especially when they deviate significantly from the account holder's usual spending patterns in NYC and nearby states.	["Unusual location", "Unknown merchant", "Unusual terminal"]
4	testaccount2	2024-10-27 13:52:37.809482	Utility Bill Payment	-245.50	debit	8098.18	4900	Online	192.168.1.3	device_123	online	completed	45.00	f	Electric Company	USD	\N	\N	Moderate risk due to online transaction for an Electric Company, which is a common merchant type, but the amount is slightly unusual.	["Amount Risk"]
9	testaccount2	2024-11-12 23:24:28.240932	Transfer to Cryptocurrency Exchange	3000.00	credit	11718.19	\N	Moscow, Russia	192.168.1.1	device_123	foreign_pos	pending	\N	f	Crypto Exchange XYZ	USD	\N	\N	\N	\N
13	testaccount2	2024-11-12 23:43:55.698314	Transfer to Cryptocurrency Exchange	-1000.00	debit	9218.19	\N	Moscow, Russia	192.168.1.1	device_123	unusual_terminal	flagged	95.00	f	Crypto Exchange XYZ	USD	\N	\N	This transaction has a high risk score due to the location being Moscow, Russia, which is outside the normal transaction patterns for a New York City resident. Additionally, the merchant being a Crypto Exchange raises concerns for potential illicit activities.	["International transaction in Moscow, Russia", "Crypto Exchange merchant"]
10	testaccount2	2024-11-12 23:33:26.370463	Transfer to Cryptocurrency Exchange	-1500.00	credit	10218.19	\N	Moscow, Russia	192.168.1.1	device_123	unusual_terminal	pending	\N	f	Crypto Exchange XYZ	USD	\N	\N	\N	\N
8	testaccount2	2024-10-28 15:17:55.261848	Luxury Purchase in Dubai	1000.00	debit	8718.19	\N	Lagos, Nigeria	192.168.1.1	device_123	card_present	flagged	95.00	f	Unknown Merchant	USD	\N	\N	This transaction poses a very high risk of fraud due to multiple concerning factors.	["Location Risk - International", "Amount Risk - Unusual for location and merchant type", "Method Risk - Card present in Lagos, Nigeria", "Pattern Risk - Unusual location, device/IP change"]
7	testaccount2	2024-10-28 15:13:21.266073	Grocery Shopping at Whole Foods	10.00	credit	7718.19	\N	New York, NY	192.168.1.1	device_123	card_present	completed	10.00	f	Whole Foods Market	USD	\N	\N	Low risk transaction based on normal NYC patterns. The transaction amount is typical for a retail purchase at Whole Foods Market in NYC, and the method used (card_present) aligns with common transaction methods in the area.	[]
11	testaccount2	2024-11-12 23:38:46.254867	Transfer to Cryptocurrency Exchange	1000.00	debit	11218.19	\N	Lagos, Nigeria	192.168.1.1	device_123	unusual_terminal	flagged	95.00	f	Crypto Exchange XYZ	USD	\N	\N	This transaction is highly suspicious based on the account holder's normal patterns. The transaction amount is significant, the location is in Lagos, Nigeria, a known high-risk area for financial fraud, and the merchant is a Crypto Exchange which can be associated with money laundering or illicit activities. The method 'unusual_terminal' raises further red flags, along with the unfamiliar device ID and IP address. Given the deviation from the account holder's usual transactions in NYC and nearby states, this transaction poses a high risk of fraud.	["Unusual location for the account holder", "High-risk merchant category", "Unfamiliar device ID and IP address"]
\.


--
-- Data for Name: useraccount; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.useraccount (id, username, password) FROM stdin;
1	devaccount	scrypt:32768:8:1$CmekhBAMXfa3eVm7$d86aaa7c0f7dc24dfa29ee0088b4d34e905506943fe807f29e9f8b001f05572892f350e4035e5cb91a9eb677af4ef9dbdd526c834bc57c41be46e127896589ac
2	test1	pass
3	testaccount2	scrypt:32768:8:1$aq2QDOUGMolVxidk$df5142ac671a492f1b4cccaca85c0aefb02d57e6dbe27be562d4b4d7cc34afa42c6e6b6063e4f37aa170a7ccbe2a04c32de5b51c8b5beaaf0d0df56ed93388ec
\.


--
-- Name: transactions_transaction_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.transactions_transaction_id_seq', 13, true);


--
-- Name: useraccount_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.useraccount_id_seq', 3, true);


--
-- Name: transactions transactions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_pkey PRIMARY KEY (transaction_id);


--
-- Name: useraccount useraccount_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.useraccount
    ADD CONSTRAINT useraccount_pkey PRIMARY KEY (id);


--
-- Name: useraccount useraccount_username_unique; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.useraccount
    ADD CONSTRAINT useraccount_username_unique UNIQUE (username);


--
-- Name: transactions transactions_username_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_username_fkey FOREIGN KEY (username) REFERENCES public.useraccount(username);


--
-- PostgreSQL database dump complete
--