let card = null;
let awaitingContinue = false;
let busy = false;
let lastInput = '';
let pendingCard = null;
let pendingStats = null;

function setStats(stats) {
    if (!stats) return;
    document.getElementById('done').innerText = stats.done;
    document.getElementById('target').innerText = stats.target;
    document.getElementById('retry').innerText = stats.retry;
    document.getElementById('remain').innerText = stats.remaining;
}

function showFinished() {
    card = null;
    awaitingContinue = false;
    document.getElementById('word').innerText = 'Today finished';
    document.getElementById('tip').innerText = '';
    document.getElementById('sen').innerText = '';
    document.getElementById('user_ans').innerText = '';
    document.getElementById('input').disabled = true;
    document.getElementById('submit').disabled = true;
    document.getElementById('finish').innerText = 'Back to wordlist';
}

function showCard(nextCard, stats) {
    setStats(stats);
    if (!nextCard || (stats && stats.finished)) {
        showFinished();
        return;
    }
    card = nextCard;
    awaitingContinue = false;
    lastInput = '';
    pendingCard = null;
    pendingStats = null;
    document.getElementById('word').innerText = card.meaning;
    document.getElementById('tip').innerText = '';
    document.getElementById('sen').innerText = '';
    document.getElementById('user_ans').innerText = '';
    document.getElementById('input').disabled = false;
    document.getElementById('submit').disabled = false;
    document.getElementById('input').value = '';
    document.getElementById('finish').innerText = '';
    document.getElementById('input').focus();
}

function showMistake() {
    awaitingContinue = true;
    document.getElementById('tip').innerText = card.word;
    document.getElementById('user_ans').innerText = lastInput;
    if (sm && card.example) {
        document.getElementById('sen').innerText = card.example;
    }
    document.getElementById('input').value = '';
}

function checkInput() {
    if (!card || busy) return;

    // After a mistake: Enter advances to the next card already returned by rate
    if (awaitingContinue) {
        showCard(pendingCard, pendingStats);
        return;
    }

    lastInput = document.getElementById('input').value;
    if (lastInput === card.word) {
        busy = true;
        fetch('/recite/rate', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({list_id: listId, word: card.word, rating: 'know'}),
            credentials: 'same-origin',
        }).then(function (res) {
            if (!res.ok) throw new Error('rate failed');
            return res.json();
        }).then(function (data) {
            showCard(data.card, data.stats);
        }).finally(function () {
            busy = false;
        });
        return;
    }

    // Wrong: save as dont, show tip, wait for second Enter
    busy = true;
    fetch('/recite/rate', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({list_id: listId, word: card.word, rating: 'dont'}),
        credentials: 'same-origin',
    }).then(function (res) {
        if (!res.ok) throw new Error('rate failed');
        return res.json();
    }).then(function (data) {
        pendingCard = data.card;
        pendingStats = data.stats;
        setStats(data.stats);
        showMistake();
    }).catch(function () {
        showMistake();
    }).finally(function () {
        busy = false;
    });
}

window.onload = function () {
    showCard(initialCard, initialStats);
};
