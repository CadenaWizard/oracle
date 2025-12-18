const url_base = "/api/v0/";

var ora_info = {};
var ora_status = {};
var event_classes = [];
var symbols = ["BTCUSD"];
var sel_symbol = 0;
var event_class = [];
var prices = {};
var price_infos = {};

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
    await load_evenclass();
    await load_prices();
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
}

async function load_evenclass() {
    event_class = await fetch_json("event/event_classes");
    await display_event_classes();
}

async function load_prices() {
    prices = await fetch_json("price/current_all");
    await display_prices();

    const cur_symbol = symbols[sel_symbol];
    price_infos = await fetch_json("price_info/current/" + cur_symbol);
    await display_price_info();
}

async function load_prices() {
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
    // htm += '</table>';
    // htm += '<table>';
    htm += '<tr><td>Total event count:</td><td>' + ora_status["total_event_count"] + '</td></tr>';
    htm += '<tr><td>TODO add period</td><td></td></tr>';
    htm += '</table>';
    document.getElementById("orainfo-display").innerHTML = htm;
}

async function display_symbols() {
    var htm = '<table class="symbols-table"><tr>';
    for (var i = 0; i < symbols.length; i++) {
        const symbol = symbols[i];
        htm += '<td><div class="symbol-group" onclick="select_symbol(' + i + ')"><span class="symbol-number" id="price-value-' + symbol + '">99999!</span><span class="symbol-name">' + symbol + '</span></div></td>';
    }
    htm += "</tr></table>";
    document.getElementById("symbols-section-display").innerHTML = htm;
}

async function select_symbol(index) {
    sel_symbol = 0
    if (symbols.length > index) {
        sel_symbol = index;
    }
    await load_evenclass();
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
        const period = eclass["repeat_period"];
        var htm = "<table>";
        htm += '<tr><td>Class ID:</td><td>' + class_id + '</td></tr>';
        htm += '<tr><td>Repeat period:</td><td>' + period + ' secs</td></tr>';
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
        var htm = '<table>';
        // don't round here
        htm += '<tr><td>Price:</td><td><strong>' + price_infos["price"] + '</strong></td></tr>';
        htm += '<tr><td>Symbol:</td><td>' + price_infos["symbol"] + '</td></tr>';
        htm += '<tr><td>Source:</td><td>' + price_infos["source"] + '</td></tr>';
        htm += '<tr><td>TODO add time</td><td></td></tr>';
        htm += '</table>';
        document.getElementById("price-details").innerHTML = htm;
    }
    {
        var htm = '<table>';
        for (var i in price_infos["aggr_sources"]) {
            var src_obj = price_infos["aggr_sources"][i];
            const price = src_obj["price"];
            const source_name = src_obj["source"];
            const error = src_obj["error"];
            // console.log(source_name, price, error);
            htm += '<tr>';
            htm += '<td><strong>' + source_name+ '</strong>:</td><td><strong>' + Math.round(price) + '</strong></td>';
            htm += '<td>TODO age</td>';
            if (error) {
                htm += '<td>' + error + '</td></tr>';
            }
            htm += '</tr>';
        }
        htm += '</table>';
        document.getElementById("price-sources").innerHTML = htm;
    }
}

