let cnt = Array(en.length).fill(2), firstime = Array(en.length).fill(true);
let idx = 0, flag = false;

function deleteWord(id) {
    en.splice(id, 1);
    zh.splice(id, 1);
    cnt.splice(id, 1);
    firstime.splice(id, 1);
    if (sm) sen.splice(id, 1)
}

function getRandomInt(min, max) {
    return Math.floor(Math.random() * (max - min)) + min;
}

function showWord() {
    flag = false;
    idx = getRandomInt(0, en.length);
    document.getElementById('word').innerText = en[idx];
    document.getElementById('sen').innerText = '';
    document.getElementById('tip').innerText = '';
    if (firstime[idx]) document.getElementById('first').innerText = 'first time';
    else document.getElementById('first').innerText = '';
    document.getElementById('remain').innerText = en.length;
    document.getElementById('wordcnt').innerText = cnt[idx];
    document.getElementById('guide').innerText = 'Please recall the meaning of the word.';
    document.getElementById('know').disabled = true;
    document.getElementById('donotknow').disabled = true;
    document.getElementById('next').disabled = false;
}

function showTip() {
    flag = true;
    document.getElementById('tip').innerText = zh[idx];
    if (sm) document.getElementById('sen').innerText = sen[idx];
    document.getElementById('guide').innerText = '';
    document.getElementById('know').disabled = false;
    document.getElementById('donotknow').disabled = false;
    document.getElementById('next').disabled = true;
}


function checkKnow() {
    cnt[idx]--;
    if (firstime[idx] || cnt[idx] === 0) {
        deleteWord(idx);
    }
    if (en.length === 0) {
        document.getElementById('know').disabled = true;
        document.getElementById('donotknow').disabled = true;
        document.getElementById('next').disabled = true;
        document.getElementById('finish').innerText = 'Finished';
    } else {
        showWord();
    }
}

function checkDonotknow() {
    firstime[idx] = false;
    cnt[idx] = 2;
    showWord();
}

document.addEventListener("keydown", function(event) {
    let key = event.key.length === 1 ? event.key.toLowerCase() : event.key; // 不区分大小写
    if (key === "s" || key === "ArrowDown") {
        if (!flag) showTip();
    }
    if (key === "a" || key === "ArrowLeft") {
        if (flag) checkKnow();
    }
    if (key === "d" || key === "ArrowRight") {
        if (flag) checkDonotknow();
    }
});

window.onload = showWord;