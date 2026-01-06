const url_base = "/api/v0/";

var ora_info = {};
var ora_status = {};
var event_classes = [];
var symbols = ["BTCUSD"];
var sel_symbol = 0;
var event_class = [];
var prices = {};
var price_infos = {};
var now = 0;

async function fetch_json(url) {
    try {
        full_url = url_base + url;
        const response = await fetch(full_url);
        if (!response.ok) {
            throw new Error(`Response status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error(error.message);
        return "";
    }
}

async function fetch_text(url) {
    try {
        full_url = url_base + url;
        const response = await fetch(full_url);
        if (!response.ok) {
            throw new Error(`Response status: ${response.status}`);
        }
        const res = await response.text();
        // const res = await response.json();
        // console.log(res);
        return res;
    } catch (error) {
        console.error(error.message);
        return "";
    }
}

async function page_load() {
    await load();
    await load_prices();

    // start auto-update of price
    var intervalId = setInterval(async function() {
        // console.log("Refresh!", Date.now() / 1000)
        await load_prices();
    }, 3000);
}

async function load() {
    ora_info = await fetch_json("oracle/oracle_info");
    ora_status = await fetch_json("oracle/oracle_status");
    await display_ora_info_and_status();

    // Get symbols from the event classes
    event_classes = await fetch_json("event/event_classes");
    // sel_symbol = 0

    symbols = [];
    for (var i = 0; i < event_classes.length; ++i) {
        const symbol = event_classes[i]["desc"]["definition"];
        symbols.push(symbol);
    }

    // console.log(event_classes.length);
    // console.log(event_classes);

    await display_symbols(symbols);

    event_class = await fetch_json("event/event_classes");
    await display_event_classes();
}

async function load_prices() {
    now = Math.floor(Date.now() / 1000);
    prices = await fetch_json("price/current_all");
    await display_prices();

    const cur_symbol = symbols[sel_symbol];
    price_infos = await fetch_json("price_info/current/" + cur_symbol);
    await display_price_info();
}

async function display_ora_info_and_status() {
    var htm = '<table>';
    htm += '<tr><td>Oracle public key:</td><td>' + ora_info["main_public_key"] + '</td></tr>';
    htm += '<tr><td>TODO add horizon</td><td></td></tr>';
    htm += '<tr><td>TODO btc address</td><td></td></tr>';
    // htm += '</table>';
    // htm += '<table>';
    htm += '<tr><td>Total event count:</td><td>' + ora_status["total_event_count"] + '</td></tr>';
    htm += '</table>';
    document.getElementById("orainfo-display").innerHTML = htm;
}

async function display_symbols() {
    var htm = '<table class="symbols-table"><tr>';
    for (var i = 0; i < symbols.length; i++) {
        const symbol = symbols[i];
        htm += '<td><div class="symbol-group" onclick="select_symbol(' + i + ')"><span class="symbol-number" id="price-value-' + symbol + '">000000</span><span class="symbol-name">' + symbol + '</span></div></td>';
    }
    htm += "</tr></table>";
    document.getElementById("symbols-section-display").innerHTML = htm;
}

async function select_symbol(index) {
    sel_symbol = 0
    if (symbols.length > index) {
        sel_symbol = index;
    }
    await display_event_classes();
    await load_prices();
}

async function display_event_classes() {
    // select event class
    const cur_symbol = symbols[sel_symbol];
    eclass = null;
    for (var i in event_classes) {
        const esymbol = event_classes[i]["desc"]["definition"];
        if (cur_symbol == esymbol) {
            eclass = event_classes[i];
        }
    }
    if (eclass) {
        const class_id = eclass["class_id"];
        const period_mins = Math.round(eclass["repeat_period"] / 60);
        var htm = "<table>";
        htm += '<tr><td>Class ID:</td><td><strong>' + class_id + '</strong></td></tr>';
        htm += '<tr><td>Repeat period:</td><td>' + period_mins + ' mins</td></tr>';
        htm += '<tr><td>TODO add next event ID</td><td></td></tr>';
        htm += '<tr><td>TODO add ID of last event with outcome</td><td></td></tr>';
        document.getElementById("eventclass-display").innerHTML = htm;
    }
}

async function display_prices() {
    for (var symbol in prices) {
        elem_name = "price-value-" + symbol;
        elem = document.getElementById(elem_name);
        if (elem) {
            elem.textContent = Math.round(prices[symbol]);
        }
    }
}

async function display_price_info() {
    {
        var htm = '<table class="details-table">';
        const price = price_infos["price"];
        const r_time = price_infos["retrieve_time"];
        const age = Math.max(now - r_time, 0);
        htm += '<tr><td>Price:</td><td><strong>' + Math.round(price) + '</strong></td></tr>';
        htm += '<tr><td>Symbol:</td><td>' + price_infos["symbol"] + '</td></tr>';
        // htm += '<tr><td>Source:</td><td>' + price_infos["source"] + '</td></tr>';
        htm += '<tr><td>Age:</td><td>' + Math.round(age) + ' s</td></tr>';
        htm += '</table>';
        document.getElementById("price-details").innerHTML = htm;
    }
    {
        var htm = '<table class="details-table">';
        for (var i in price_infos["aggr_sources"]) {
            var src_obj = price_infos["aggr_sources"][i];
            const price = src_obj["price"];
            const source_name = src_obj["source"];
            const r_time = src_obj["retrieve_time"];
            const age = Math.max(now - r_time, 0);
            const delta = Math.round(src_obj["delta_from_aggr"])
            var delta_s = delta.toString();
            if (delta > 0) {
                delta_s = "+" + delta_s;
            }
            const error = src_obj["error"];
            // console.log(source_name, price, error);
            htm += '<tr>';
            htm += '<td><strong>' + source_name+ '</strong>:</td>';
            if (!error) {
                htm += '<td><strong>' + Math.round(price) + '</strong></td>';
                htm += '<td>' + delta_s + '</td>';
                htm += '<td>' + Math.round(age) + ' s</td>';
            } else {
                htm += '<td colspan="3">' + error + '</td></tr>';
            }
            htm += '</tr>';
        }
        htm += '</table>';
        document.getElementById("price-sources").innerHTML = htm;
    }
}

