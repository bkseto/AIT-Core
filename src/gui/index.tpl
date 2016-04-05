<!DOCTYPE html>
<html>

<head>
  <meta charset="utf-8">
  <title>OCO-3 GUI</title>
  <meta name="viewport"    content="width=device-width, initial-scale=1">
  <meta name="description" content="OCO-3 GUI">
  <meta name="author"      content="E. Hovland, J. Padams, B. Bornstein">

  <link rel="stylesheet" type="text/css" media="screen" href="css/bootstrap.min.css"/>
  <link rel="stylesheet" type="text/css" media="screen" href="css/font-awesome.min.css">
  <link rel="stylesheet" type="text/css" media="screen" href="css/typeahead.css">
  <link rel="stylesheet" type="text/css" media="screen" href="css/style.css"/>
</head>

<body>

% include('navbar.html')

  <div class="container">

% include('telem.html')

    <!-- Tab panes -->
    <div class="row" style="padding-top: 20px;">
      <div role="tabpanel">

        <!-- Nav tabs -->
        <ul class="nav nav-tabs" role="tablist">
          <li role="presentation" class="active"><a href="#cmd-tab" aria-controls="cmd-tab" role="tab" data-toggle="tab">Commanding</a></li>
          <li role="presentation"><a href="#seq-tab" aria-controls="seq-tab" role="tab" data-toggle="tab">Sequences</a></li>
        </ul>
        <br />
        <div class="col-sm-6 tab-content">
          <div role="tabpanel" class="tab-pane active" id="cmd-tab">
            <form class="form-horizontal" role="form" method="POST" action="/cmd" id="form-cmd">
              <label>Send Command:</label>
              <div id="cmd-input-group" class="input-group">
                <input type="text" id="command" name="command" placeholder="OCO3_CORE_NO_OP" class="form-control">
                <span class="input-group-btn">
                  <button id="send-cmd-btn" type="submit" class="btn btn-success">Send</button>
                </span>
              </div>
              <small>(or Ctrl-Enter to Send)</small>
            </form>
          </div> <!-- /.tabpanel -->
          <div role="tabpanel" class="tab-pane" id="seq-tab">
              <form class="form-horizontal" role="form" method="POST" action="/seq" id="form-seq">
                <div class="form-group">
                  <label style="width:50%">Send Sequence:</label>
                  <div style="width:50%; float:right; text-align:right;">
                    <button type="button" class="btn btn-default seq-refresh-btn" style="line-height:75%; font-size:75%"><span class="glyphicon glyphicon-refresh" aria-hidden="true"></span> Refresh</button>
                  </div>
                  <select class="form-control" multiple="true" id="seqfile" name="seqfile">
                  </select>
                </div>
                <div class="form-group">
                  <button id="send-seq-btn" type="submit" class="btn btn-success">Send</button>
                </div>
              </form>
          </div> <!-- /.tabpanel -->

        </div> <!-- /.col-sm-12 .tab-content -->
      </div>
    </div> <!-- /.row -->
    <hr />

% include('logs.html')

  </div> <!-- /.container -->


<script type="text/javascript" src="js/jquery.min.js"></script>
<script type="text/javascript" src="js/bootstrap.min.js"></script>
<script type="text/javascript" src="js/highcharts.js"></script>
<script type="text/javascript" src="js/typeahead.bundle.min.js"></script>
<script type="text/javascript" src="js/oco3.js"></script>
<script type="text/javascript" src="js/sprintf.js"></script>
<script type="text/javascript" src="js/strftime.js"></script>
<script type="text/javascript">
$(function() {
    var gui_host       = window.location.host
    var tlmStale       = 0;
    var ptlmStale      = 0;
    var ws             = new WebSocket('ws://' + gui_host + '/tlm/stream');
    var pws            = new WebSocket('ws://' + gui_host + '/tlm/psu');
    var tlmIntervalID  = 0;
    var ptlmIntervalID = 0;

var chart = new Highcharts.Chart({
            chart: {
                zoomType: 'x',
                renderTo: 'telem-thermal-plot'
            },
            title: {
                text: ''
            },
            xAxis: {
                type: 'datetime'
            },
            yAxis: {
                title: {
                    text: 'DN'
                }
            },
            legend: {
                enabled: true,
                useHTML: true
            },
            credits: {
                enabled: false
            },
            plotOptions: {
                area: {
                    fillColor: {
                        linearGradient: {
                            x1: 0,
                            y1: 0,
                            x2: 0,
                            y2: 1
                        },
                        stops: [
                            [0, Highcharts.getOptions().colors[0]],
                            [1, Highcharts.Color(Highcharts.getOptions().colors[0]).setOpacity(0).get('rgba')]
                        ]
                    },
                    marker: {
                        radius: 2
                    },
                    lineWidth: 1,
                    states: {
                        hover: {
                            lineWidth: 1
                        }
                    },
                    threshold: null
                }
            }
       });

    window.chart = chart;

    var getSimBtn = function (sim) {
        return $('.sim-btn[data-sim="' + sim + '"]');
    }


    var init = function () {
        $('[data-field]').text('N/A');
        populateSeqList();
    }


    var populateSeqList = function () {
        var list = $('#seqfile');


        $.getJSON('/seq', function (data, status) {
            list.empty();
            $.each(data, function (index, value) {
                list.append($('<option/>', { value: value, text: value }));
            });
        });
    }


    var reportTLMStale = function () {
        if (tlmStale > 0) {
            setLEDState($('#tlm-status i'), 'pending');
        }
        tlmStale++;
    }

    var reportPTLMStale = function () {
        if (ptlmStale > 0) {
            setLEDState($('#ptlm-status i'), 'pending');
        }
        ptlmStale++;
    }

    var setSimBtnState = function (btn, event) {
        var currState = btn.data('state');
        var nextState = event;
        var led       = btn.children('i');


        if (nextState === 'on' || nextState === 'off') {
            btn.data('state', nextState);
        }

        if (event === 'mouseover') {
            var classes  = 'fa ';
            classes     += currState === 'on' ? 'fa-stop stop' : 'fa-play start';
            led.removeClass().addClass(classes);
        }
        else if (event === 'mouseout') {
            setLEDState(led, currState);
        }
        else {
            setLEDState(led, nextState);
        }
    }


    var setLEDState = function (led, state) {
        led.removeClass().addClass('fa fa-circle status-' + state);
    }


    ws.binaryType = 'arraybuffer';
    ws.onopen = function() {
        setLEDState($('#tlm-status i'), 'pending');
        tlmIntervalID = setInterval(reportTLMStale, 1000);
    };

    ws.onclose = function () {
        setLEDState($('#tlm-status i'), 'off');
        clearInterval(tlmIntervalID);
    }

    ws.onmessage = function (evt) {
        if (evt.data instanceof ArrayBuffer) {
            clearInterval(tlmIntervalID);
            updateUI( new DataView(evt.data, 1) );
            setLEDState($('#tlm-status i'), 'on');

            tlmStale      = 0;
            tlmIntervalID = setInterval(reportTLMStale, 1000);
        }
    };


    pws.onopen = function() {
        setLEDState($('#ptlm-status i'), 'pending');
        pltmIntervalID = setInterval(reportPTLMStale, 1000);
    };

    pws.onclose = function () {
        setLEDState($('#ptlm-status i'), 'off');
        clearInterval(ptlmIntervalID);
    }

    pws.onmessage = function (evt) {
        clearInterval(ptlmIntervalID)
        setLEDState($('#ptlm-status i'), 'on');
        var data = $.parseJSON(evt.data);
        $('[data-field="PSU_timestamp"]').text(data.timestamp)
        $('[data-field="vout"]').text(data.vout)
        $('[data-field="vset"]').text(data.vset)
        $('[data-field="iout"]').text(data.iout)
        $('[data-field="iset"]').text(data.iset)
        ptlmStale = 0;
        ptlmIntervalID = setInterval(reportPTLMStale, 3000);
    };


    $container = $('#gds-log .logging-table');
    $container[0].scrollTop = $container[0].scrollHeight;

    var es = new EventSource('/log');
    es.onmessage = function (e) {
        var data = $.parseJSON(e.data);

        // Get the css class from the log level
        var context = 'log-' + $.trim(data.levelname).toLowerCase();

       // Apply context and output the row in the table
       $('#gds-log-table tbody').append(
           '<tr class="' + context + '"><td width="20%">'
           + data.asctime   + '</td><td width="10%">'
           + data.levelname + '</td><td>'
           + data.message   + '</td></tr>');

       $container.scrollTop($container[0].scrollHeight)
    };


    var source = new EventSource('/events');

    source.addEventListener('message', function (event) {
        var event = $.parseJSON(event.data);
        $(document).trigger(event.name, event.data);
    });


    $(document).on('cmd:hist', function (event, cmdname) {
        oco3.cmd.typeahead.hist.add([ cmdname ]);
    });

    $(document).on('sim:on sim:off sim:pending', function (event, sim) {
        setSimBtnState( getSimBtn(sim), event.type.split(':')[1] );
    });

    $(document).on('seq:exec', function (event, seqf) {
        $('#send-cmd-btn, #send-seq-btn').prop('disabled', true);
    });

    $(document).on('seq:done seq:err', function (event, seqf) {
        $('#send-cmd-btn, #send-seq-btn').prop('disabled', false);
    });


    $('#command, #seqfile')
        .keyup  ( function (e) {
            if (e.keyCode == 17) {
                $(this).data('ctrl',  false);
            }
        })
        .keydown( function (e) {
            if (e.keyCode == 17) {
                $(this).data('ctrl',  true);
            }
            else if (e.keyCode == 13 && !$(this).data('ctrl')) {
                e.preventDefault();
                return false;
            }

            return true;
        });

    $('#form-cmd').submit( function () {
        var url  = $(this).attr('action');
        var data = $(this).serialize();

        $.ajax({ type: 'POST', url: url, data: data });

        $('#command').focus();

        return false;
    });

    $('#form-seq').submit( function () {
        var url  = $(this).attr('action');
        var data = $(this).serialize();
        var $btn = $(this);

        $btn.prop('disabled', true);

        $.ajax({
            type: 'POST',
            url:  url,
            data: data,
            error:    function (request, status, error) { console.log(error); },
            complete: function (request, status) { $btn.prop('disabled', false); }
        });

        $('#seqfile').focus();

        return false;
    });


    $('.seq-refresh-btn' ).on('click', function() {
        populateSeqList();
        return false;
    });

    $('.sim-btn').on('click', function (event) {
        var btn   = $(this);
        var sim   = btn.data('sim');
        var state = btn.data('state');
        var url   = '/sim/' + sim;

        if (state === 'off') {
            $.post(url + '/start');
        }
        else if (state === 'on') {
            $.post(url + '/stop');
        }

        event.preventDefault();
        return false;
    });

    $('.sim-btn').on('mouseover mouseout', function (event) {
        setSimBtnState( $(this), event.type );
    });

    $('table.telem td:not([data-field])').on('click', function (event) {
      var name   = $(this).html().replace(':', '');
      var field  = $(this).next('[data-field]').first();
      var series = chart.addSeries({ type: 'area', name: name, data: [ ] });
      field.data('plot-series', series);
    });

    init();
});
</script>

</body>
</html>
