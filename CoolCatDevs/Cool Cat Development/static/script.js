function getpokercolor(Color) {
    switch (Color) {
        case "Black":
            poker_tee(src = "{{ url_for('static', filename='product_images/poker_tee_black.png') }} ");
            break;
        case "White":
            poker_tee(src = "{{ url_for('static', filename='product_images/poker_tee_white.png') }} ");
            break;
        case "Blue":
            poker_tee.src = "{{ url_for('static', filename='product_images/poker_tee_blue.png') }} ";
            break;
        case "Red":
            poker_tee.src = "{{ url_for('static', filename='product_images/poker_tee_red.png') }} ";
            break;

    }
}
function getcnscolor(Black, White, Blue, Red) {
    switch (document.getElementById(cns_tee)) {
        case Black:
            cns_tee(src = "{{ url_for('static', filename='product_images/poker_tee_black.png') }} ");
            break;
        case White:
            cns_tee(src = "{{ url_for('static', filename='product_images/poker_tee_white.png') }} ");
            break;
        case Blue:
            cns_tee.src = "{{ url_for('static', filename='product_images/poker_tee_blue.png') }} ";
            break;
        case Red:
            cns_tee.src = "{{ url_for('static', filename='product_images/poker_tee_red.png') }} ";
            break;
    }
}
function getmoneycolor(Black, White, Blue, Red) {
    switch (document.getElementById(money_tee)) {
        case Black:
           money_tee(src = "{{ url_for('static', filename='product_images/poker_tee_black.png') }} ");
            break;
        case White:
            money_tee(src = "{{ url_for('static', filename='product_images/poker_tee_white.png') }} ");
            break;
        case Blue:
            money_tee.src = "{{ url_for('static', filename='product_images/poker_tee_blue.png') }} ";
            break;
        case Red:
            money_tee.src = "{{ url_for('static', filename='product_images/poker_tee_red.png') }} ";
            break;

    }
}
function test() {
    var color = document.getElementsByName(Select)
}
 