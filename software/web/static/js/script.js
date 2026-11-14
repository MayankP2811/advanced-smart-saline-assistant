// Shared scripts for the Smart Saline dashboard.

// Send the CSRF token with every same-site POST made through jQuery.
$.ajaxSetup({
  beforeSend: function (xhr, settings) {
    if (settings.type === 'POST' && !/^https?:\/\//.test(settings.url)) {
      xhr.setRequestHeader('X-CSRF-Token', $('meta[name="csrf-token"]').attr('content'));
    }
  }
});

function filterPatients() {
  var term = $('#searchInput').val().toLowerCase();
  $('#patientList > .col-md-3').each(function () {
    $(this).toggle($(this).find('.card-title').text().toLowerCase().includes(term));
  });
}

// Vital-sign limits used for the "Check vitals" warning.
var VITALS = {minHeartRate: 50, maxHeartRate: 120, minTempC: 35.0, maxTempC: 38.0};

function formatTemp(raw) {
  // The bedside node sends temperature in tenths of a degree C; 0 or missing means no reading yet.
  return raw ? (raw / 10).toFixed(1) : '—';
}

function formatHeartRate(bpm) {
  return bpm ? String(bpm) : '—';
}

function vitalsWarning(data) {
  if (!data || !data.online) return '';
  var problems = [];
  if (data.e && (data.e < VITALS.minHeartRate || data.e > VITALS.maxHeartRate)) problems.push('heart rate ' + data.e + ' bpm');
  if (data.f) {
    var c = data.f / 10;
    if (c < VITALS.minTempC || c >= VITALS.maxTempC) problems.push('temperature ' + c.toFixed(1) + ' °C');
  }
  return problems.join(', ');
}

function showMessage(container, message, category) {
  $(container).html($('<div class="alert" role="alert">').addClass('alert-' + category).text(message));
}

// Live readings on the dashboard cards.
$(function () {
  $('.card[data-channel]').each(function () {
    var card = $(this);
    var channel = card.data('channel');
    function render(data) {
      ['b', 'c', 'd'].forEach(function (field) {
        card.find('.data-' + field).text(data && data[field] !== undefined ? data[field] : '—');
      });
      card.find('.data-e').text(formatHeartRate(data && data.e));
      card.find('.data-f').text(formatTemp(data && data.f));
      card.find('.card-footer1').toggle(!data || !data.online);
      card.find('.card-footer2').toggle(Boolean(data && data.online && (data.b < 3 || data.b > 80)));
      var warning = vitalsWarning(data);
      card.find('.vitals-msg').text(warning);
      card.find('.card-footer3').toggle(Boolean(warning));
    }
    function poll() {
      $.ajax({url: '/node' + channel, dataType: 'json', success: render,
        error: function (xhr) { render(xhr.responseJSON || null); },
        complete: function () { window.setTimeout(poll, 1000); }
      });
    }
    poll();
  });
});

// Security code step used by the registration and therapy forms.
// The server checks the code again when the form arrives.
var securityTargetForm = null;

function openSecurityCheck(formId) {
  var form = document.getElementById(formId);
  if (!form.reportValidity()) return;
  securityTargetForm = form;
  $('#messageContainer').empty();
  $('#securityCodeInput').val('');
  $('.modal').modal('hide');
  $('#securityModal').modal('show');
}

function submitWithSecurityCode() {
  var code = $('#securityCodeInput').val();
  $.post('/check_password', {enteredPassword: code})
    .done(function (response) {
      if (!response.success) {
        showMessage('#messageContainer', 'Incorrect security code.', 'danger');
        return;
      }
      $(securityTargetForm).find('.security-code-field').val(code);
      securityTargetForm.submit();
    })
    .fail(function () { showMessage('#messageContainer', 'Could not check the code. Try again.', 'danger'); });
}

function startTherapy() {
  var form = document.getElementById('ivForm');
  if (!form.reportValidity()) return;
  $.post('/check_stat', {channel: $('#channel').val()})
    .done(function (response) {
      if (response.status) {
        showMessage('#ivMessage', 'This channel is already in use. Choose another one.', 'warning');
      } else {
        openSecurityCheck('ivForm');
      }
    })
    .fail(function () { showMessage('#ivMessage', 'Could not check the channel. Try again.', 'danger'); });
}
