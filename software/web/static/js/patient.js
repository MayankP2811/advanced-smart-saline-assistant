// Patient page: live readings, time remaining and device commands.
$(function () {
  var therapy = $('#therapy');
  if (!therapy.length) return;
  var channel = therapy.data('channel');
  var history = [];

  function drawSparkline() {
    var svg = document.getElementById('sparkline');
    if (!svg || history.length < 2) return;
    var w = svg.width.baseVal.value, h = svg.height.baseVal.value;
    var min = Math.min.apply(null, history), max = Math.max.apply(null, history);
    var span = max - min || 1;
    var points = history.map(function (v, i) {
      return (i * w / (history.length - 1)).toFixed(1) + ',' + (h - 2 - (v - min) * (h - 4) / span).toFixed(1);
    }).join(' ');
    svg.innerHTML = '<polyline points="' + points + '"></polyline>';
  }

  function render(data) {
    var fields = {element2: 'b', element3: 'c', element4: 'd'};
    Object.keys(fields).forEach(function (id) {
      $('#' + id).text(data && data[fields[id]] !== undefined ? data[fields[id]] : '—');
    });
    $('#element5').text(formatHeartRate(data && data.e));
    $('#element6').text(formatTemp(data && data.f));
    var warning = vitalsWarning(data);
    $('.vitals-alert').toggle(Boolean(warning)).text(warning ? 'Check vitals: ' + warning : '');
    var online = Boolean(data && data.online);
    $('#nodeStatus').text(online ? '· connected' : '· not connected');
    $('.alertshow').toggle(!online).text(data && data.error ? data.error : 'No fresh readings — values shown may be old.');
    if (online) {
      history.push(data.b);
      if (history.length > 30) history.shift();
      drawSparkline();
    }
  }

  function poll() {
    $.ajax({url: '/node' + channel, dataType: 'json', success: render,
      error: function (xhr) { render(xhr.responseJSON || null); },
      complete: function () { window.setTimeout(poll, 1000); }
    });
  }
  poll();

  var remaining = Number(therapy.data('remaining'));
  function tick() {
    var h = Math.floor(remaining / 3600), m = Math.floor(remaining % 3600 / 60), s = remaining % 60;
    $('#timeRemaining').text([h, m, s].map(function (n) { return String(n).padStart(2, '0'); }).join(':'));
    if (remaining > 0) remaining -= 1;
  }
  tick();
  window.setInterval(tick, 1000);
});

function postCommand(url, payload, done) {
  $.ajax({url: url, type: 'POST', contentType: 'application/json', data: JSON.stringify(payload),
    success: function (response) {
      var command = response.command || response;
      alert((response.record_saved ? 'New rate saved. ' : '') + (command.message || 'Done.'));
      if (done) done(response);
    },
    error: function (xhr) {
      var body = xhr.responseJSON || {};
      var command = body.command || body;
      alert((body.record_saved ? 'New rate saved. ' : '') + (command.message || 'Request failed. No device action was confirmed.'));
      if (body.record_saved && done) done(body);
    }
  });
}

function sendStartStop(value) {
  postCommand('/buttons', {ch: $('#therapy').data('channel'), value: value});
}

function changeDropRate() {
  var rate = Number($('#dprate').val());
  if (!Number.isInteger(rate) || rate < 1 || rate > 255) {
    alert('Enter a whole number between 1 and 255 drops/min.');
    return;
  }
  var therapy = $('#therapy');
  postCommand('/update_drop_rate', {ch: therapy.data('channel'), RegID: therapy.data('regid'), dropRate: rate},
    function () { window.location.reload(); });
}
