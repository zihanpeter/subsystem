let card = null;
let revealed = false;
let busy = false;

function setStats(stats) {
    if (!stats) return;
    document.getElementById('done').innerText = stats.done;
    document.getElementById('target').innerText = stats.target;
    document.getElementById('retry').innerText = stats.retry;
    document.getElementById('remain').innerText = stats.remaining;
}

function showFinished() {
    card = null;
    revealed = false;
    document.getElementById('word').innerText = 'Today finished';
    document.getElementById('tip').innerText = '';
    document.getElementById('sen').innerText = '';
    document.getElementById('guide').innerText = 'You have completed today\'s words for this list.';
    document.getElementById('know').disabled = true;
    document.getElementById('donotknow').disabled = true;
    document.getElementById('next').disabled = true;
    document.getElementById('finish').innerText = 'Back to wordlist';
}

function showCard(nextCard, stats) {
    setStats(stats);
    if (!nextCard || (stats && stats.finished)) {
        showFinished();
        return;
    }
    card = nextCard;
    revealed = false;
    document.getElementById('word').innerText = card.word;
    document.getElementById('tip').innerText = '';
    document.getElementById('sen').innerText = '';
    document.getElementById('guide').innerText = 'Please recall the meaning of the word.';
    document.getElementById('know').disabled = true;
    document.getElementById('donotknow').disabled = true;
    document.getElementById('next').disabled = false;
    document.getElementById('finish').innerText = '';
}

function showTip() {
    if (!card || revealed || busy) return;
    revealed = true;
    document.getElementById('tip').innerText = card.meaning;
    if (sm && card.example) {
        document.getElementById('sen').innerText = card.example;
    }
    document.getElementById('guide').innerText = '';
    document.getElementById('know').disabled = false;
    document.getElementById('donotknow').disabled = false;
    document.getElementById('next').disabled = true;
}

function rate(rating) {
    if (!card || !revealed || busy) return;
    busy = true;
    var word = card.word;
    fetch('/recite/rate', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({list_id: listId, word: word, rating: rating}),
        credentials: 'same-origin',
    }).then(function (res) {
        if (!res.ok) throw new Error('rate failed');
        return res.json();
    }).then(function (data) {
        showCard(data.card, data.stats);
    }).catch(function () {
        document.getElementById('guide').innerText = 'Could not save progress. Try again.';
    }).finally(function () {
        busy = false;
    });
}

function checkKnow() {
    rate('know');
}

function checkDonotknow() {
    rate('dont');
}

document.addEventListener('keydown', function (event) {
    var key = event.key.length === 1 ? event.key.toLowerCase() : event.key;
    if (key === 's' || key === 'ArrowDown') {
        if (!revealed) showTip();
    }
    if (key === 'a' || key === 'ArrowLeft') {
        if (revealed) checkKnow();
    }
    if (key === 'd' || key === 'ArrowRight') {
        if (revealed) checkDonotknow();
    }
});

window.onload = function () {
    showCard(initialCard, initialStats);
};
