window.addEventListener("load", function () {
    const messagesBox = document.querySelector(".messages-box");
    if (messagesBox) {
        messagesBox.scrollTop = messagesBox.scrollHeight;
    }
});