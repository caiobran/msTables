# cryptocompare.com

https://min-api.cryptocompare.com/documentation/websockets?api_key=defaca9517739758ddb3b0dc7d9aa6382c50ac1baff8cd1a994524e0e71834aa
How To Connect
 Channels
Trade
Ticker
Aggregate Index (CCCAGG)
OHLC Candles
Full Volume
Top Tier Full Volume
Order Book L2
Top of Order Book
 Helper Endpoints
How To Connect
The CryptoCompare streaming API can be accessed via a websocket connection. Once connected, users can subscribe and unsubscribe to channels. Helper API endpoints can be used to find all the desired channels, for example top pairs per volume or market cap, top exchanges by pair, etc. You will need an API key to be able to stream data.
WebSocket Base URL: wss://streamer.cryptocompare.com/v2
Authentication
To be able to stream data you will need an API key. There are 2 ways of passing an API key:
API KEY in URL - just append ? or &api_key={your_api_key} the the end of your connection url (e.g. wss://streamer.cryptocompare.com/v2?api_key={your_api_key})
KEY in HEADER - add the following header to your request: authorization: Apikey {your_api_key}.
 Read this tutorial on how to generate a free API key
Some channels are only available for Commercial, Commercial Pro or Enterprise customers. Please refer to the Pricing page for further information.
Subscription
Once connected, subscribe to your desired channels using the subscription ID. For example to subscribe to the CryptoCompare Aggregate Index for Bitcoin in USD, your subscription ID will be 5~CCCAGG~BTC~USD. You can send a list of subscriptions in an array to subscribe to all channels of interest at once.
Your subscription message should be:
{
    "action": "SubAdd",
    "subs": ["5~CCCAGG~BTC~USD", "0~Coinbase~ETH~USD", "2~Binance~BTC~USDT"]
}
Your unsubscribe message should be:
{
    "action": "SubRemove",
    "subs": ["5~CCCAGG~BTC~USD", "0~Coinbase~ETH~USD", "2~Binance~BTC~USDT"]
}
You can subscribe to the following channels:
Type	Channel	Subscription	Example
0	Trade	0~{exchange}~{base}~{quote}	0~Coinbase~BTC~USD
2	Ticker	2~{exchange}~{base}~{quote}	2~Coinbase~BTC~USD
5	Aggregate Index (CCCAGG)	5~CCCAGG~{base}~{quote}	5~CCCAGG~BTC~USD
8	Order Book L2	8~{exchange}~{base}~{quote}	8~Coinbase~BTC~USD
11	Full Volume	11~{base}	11~BTC
21	Full Top Tier Volume	21~{base}	21~BTC
24	OHLC Candles	24~{exchange or CCCAGG}~{base}~{quote}	24~CCCAGG~BTC~USD
30	Top of Order Book	30~{exchange}~{base}~{quote}	30~Coinbase~BTC~USD
Re-connection or stale connection logic
You should always wait at least 5 seconds to reconnect if we disconnect your socket client or you decide to disconnect and reconnect.
Reasons for disconnection:
You have tried to connect too many times in a short time interval if you connect and disconnect more than 60 times a minute you will be refused access for at least 1 minute.
Everyone is disconnected at least once a week we do this in order to force everyone to reconnect and reauthorize, this removes stale connections and makes sure subscriptions that have expired are treated correctly.
Everyone is disconnected when we deploy a new version of our streaming infrastructure. We can deploy with no disconnect on a polling API but for streaming we have to break the connection.
If a socket is slow or unresponsive. We send pings every 30 seconds and monitor the response time from each socket. If a socket client takes longer than 10 seconds to respond to two consecutive pings we disconnect the socket. The Pong messages should be sent automatically by your websocket implementation as they are part of the websocket spec. If you are using a standard library for websockets this will be handled automatically for you.
Our underlying cloud (Azure) infrastruture fails. We run over 20 load balanced streaming servers, if the server you are connected to fails (or if the underlying Azure hypervisor fails) the load balancer should assign you to a new server in less than 30 seconds.
Stale connection logic / reasons to drop connection and reconnect on your side:
You have not received a heartbeat messages for more than 1 minute. We automatically send a heartbeat message per socket every 30 seconds, if you miss two heartbeats it means your connection might be stale.
You can, at any point, send us a Ping message and we'll automatically respond with a Pong. You can use this to test latency or connection stability. We advise not to send more than one Ping every 30 seconds.
Message Types
Once connected, the following response messages will be sent to acknowledge your actions or raise any errors.
Type	Message	Description
20	STREAMERWELCOME	Your first message on connection. It has information about your rate limits on opening sockets, server stats and other useful debugging information.
16	SUBSCRIBECOMPLETE	Subscription done and first payload sent.
3	LOADCOMPLETE	All subscriptions done and all payloads sent.
17	UNSUBSCRIBECOMPLETE	Subscription removal done.
18	UNSUBSCRIBEALLCOMPLETE	All subscription removals done.
999	HEARTBEAT	Message sent every 1 minute
401	UNAUTHORIZED	Your API key is missing or invalid, or does not have access to requested data.
429	RATE_LIMIT_OPENING_SOCKETS_TOO_FAST	Please spread out opening new connections. The limits are: month: 20000, day: 10000, hour: 1200, minute: 60, second: 30.
429	TOO_MANY_SOCKETS_MAX_{X}_PER_CLIENT	Number of open sockets exceeded maximum. (For free API keys, this is 1)
429	TOO_MANY_SUBSCRIPTIONS_MAX_{X}_PER_SOCKET	Number of subscriptions exceeded maximum. (For free API keys, this is 600)
500	INVALID_JSON	Sent message was invalid JSON.
500	INVALID_SUB	Subscription is invalid.
500	INVALID_PARAMETER	Invalid message parameter. Either invalid action or subs format.
500	SUBSCRIPTION_UNRECOGNIZED	Subscription to be removed not found.
500	SUBSCRIPTION_ALREADY_ACTIVE	You subscribed to a channel that already exists
500	FORCE_DISCONNECT	You had two slow (over 10 seconds) pong responses in a row. Please reconnect.
Examples
Type	Response
20	{"TYPE":"20", "MESSAGE":"STREAMERWELCOME", "SERVER_UPTIME_SECONDS":6, "SERVER_NAME":"ccc-streamer01", "SERVER_TIME_MS":1593768260252, "CLIENT_ID":5509, "DATA_FORMAT":"JSON", "SOCKETS_ACTIVE":1, "SOCKETS_REMAINING":0, "RATELIMIT_MAX_SECOND":30, "RATELIMIT_MAX_MINUTE":60, "RATELIMIT_MAX_HOUR":1200, "RATELIMIT_MAX_DAY":10000, "RATELIMIT_MAX_MONTH":20000, "RATELIMIT_REMAINING_SECOND":29, "RATELIMIT_REMAINING_MINUTE":59, "RATELIMIT_REMAINING_HOUR":1199, "RATELIMIT_REMAINING_DAY":9999, "RATELIMIT_REMAINING_MONTH":19981}
16	{"TYPE":"16", "MESSAGE":"SUBSCRIBECOMPLETE", "SUB":"0~Coinbase~ETH~BTC"}
3	{"TYPE":"3", "MESSAGE":"LOADCOMPLETE", "INFO":"All your valid subs have been loaded."}
17	{"TYPE":"17", "MESSAGE":"UNSUBSCRIBECOMPLETE", "SUB":"0~Coinbase~ETH~BTC"}
18	{"TYPE":"18", "MESSAGE":"UNSUBSCRIBEALLCOMPLETE", "INFO":"Removed 1 subs.", "INFO_OBJ":{"valid":1, "invalid":0}}
999	{"TYPE":"999", "MESSAGE":"HEARTBEAT", "TIMEMS":1582817678330}
401	{"TYPE":"401", "MESSAGE":"UNAUTHORIZED","PARAMETER": "format","INFO":"We only support JSON format with a valid api_key."}
