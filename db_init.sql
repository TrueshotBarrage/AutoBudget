CREATE TABLE IF NOT EXISTS folders (
  id smallserial PRIMARY KEY,
  email_server text NOT NULL,
  folder_name text NOT NULL,
  last_trans_date date
);

CREATE TABLE IF NOT EXISTS messages (
  id varchar(30) PRIMARY KEY,
  folder_id smallint NOT NULL REFERENCES folders (id),
  content text,
  transaction_date date NOT NULL,
  transaction_vendor varchar(40) NOT NULL,
  transaction_amount numeric(10,2) NOT NULL,
  loaded_at timestamp NOT NULL DEFAULT NOW()
);
