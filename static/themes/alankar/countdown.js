$(document).ready( function(){
    // setup countdown
    var pyconDate = new Date();
    pyconDate = new Date(2010, 7, 25);
    $('#defaultCountdown').countdown({
        until: pyconDate,
        format: 'DHMS',
        layout: '<div id="t7_timer">'+
                    '<div id="t7_vals">'+
                        '<div id="t7_d" class="t7_numbs">{dnn}</div>'+
                        '<div id="t7_h" class="t7_numbs">{hnn}</div>'+
                        '<div id="t7_m" class="t7_numbs">{mnn}</div>'+
                        '<div id="t7_s" class="t7_numbs">{snn}</div>'+
                    '</div>'+
                    '<div id="t7_labels">'+
                        '<div id="t7_dl" class="t7_labs">days</div>'+
                        '<div id="t7_hl" class="t7_labs">hours</div>'+
                        '<div id="t7_ml" class="t7_labs">mins</div>'+
                        '<div id="t7_sl" class="t7_labs">secs</div>'+
                    '</div>'+
                    '<div id="t7_timer_over"></div>'+
                '</div>'
    });
});