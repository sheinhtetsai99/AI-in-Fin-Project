-- CREATE TABLE USERACCOUNT (
-- 	ID SERIAL PRIMARY KEY,
-- 	USERNAME VARCHAR(100) NOT NULL,
-- 	PASSWORD VARCHAR(300) NOT NULL
-- )
ALTER TABLE USERACCOUNT
ADD CONSTRAINT USERACCOUNT_USERNAME_UNIQUE UNIQUE (USERNAME);

-- INSERT INTO
-- 	USERACCOUNT (USERNAME, PASSWORD)
-- VALUES
-- 	(
-- 		'test1',
-- 		'pass'
-- 	)
-- SELECT
-- 	*
-- FROM
-- 	USERACCOUNT
-- CREATE TABLE transactions (
--     transaction_id SERIAL PRIMARY KEY,
--     username VARCHAR(100) NOT NULL,
--     transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
--     description VARCHAR(255),
--     amount DECIMAL(10,2),
--     transaction_type VARCHAR(20) CHECK (transaction_type IN ('credit', 'debit')),
--     balance_after DECIMAL(10,2),
--     FOREIGN KEY (username) REFERENCES useraccount(username)
-- );
-- -- Insert sample transactions for testaccount2
-- INSERT INTO transactions (username, description, amount, transaction_type, balance_after) VALUES
-- ('testaccount2', 'Initial Deposit', 5000.00, 'credit', 5000.00),
-- ('testaccount2', 'Grocery Shopping', -156.32, 'debit', 4843.68),
-- ('testaccount2', 'Salary Deposit', 3500.00, 'credit', 8343.68),
-- ('testaccount2', 'Utility Bill Payment', -245.50, 'debit', 8098.18),
-- ('testaccount2', 'Restaurant Payment', -89.99, 'debit', 8008.19),
-- ('testaccount2', 'ATM Withdrawal', -200.00, 'debit', 7808.19),
-- ('testaccount2', 'Online Transfer Received', 150.00, 'credit', 7958.19),
-- ('testaccount2', 'Mobile Phone Bill', -75.00, 'debit', 7883.19),
-- ('testaccount2', 'Investment Dividend', 125.50, 'credit', 8008.69),
-- ('testaccount2', 'Car Insurance Payment', -175.00, 'debit', 7833.69);

SELECT
	*
FROM
	TRANSACTIONS