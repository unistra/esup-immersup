// default dates settings
var _dates_options = { dateStyle: 'long' };
var _dates_locale = navigator.languages !== undefined ? navigator.languages[0] : navigator.language;

function getCookie(name) {
  var cookieValue = null
  if (document.cookie && document.cookie != '') {
    var cookies = document.cookie.split(';')
    for (var i = 0; i < cookies.length; i++) {
      var cookie = $.trim(cookies[i])
      // Does this cookie string begin with the name we want?
      if (cookie.substring(0, name.length + 1) == (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1))
        break
      }
    }
  }

  return cookieValue
}

function initFeedback(obj) {
  $(document).on('showFeedback', function (event, ...messages) {
    var $target = $(event.target).empty()
    messages.forEach(function (element) {
      $target.append(
        $('<div/>', {
          'class': 'messages alert alert-dismissible alert-' + element[1],
          'text': element[0]
        }).append(
          $('<a>', {
            'href': '#',
            'class': 'close',
            'data-dismiss': 'alert',
            'aria-label': 'close',
            'text': '×'
          })
        )
      )
    })
  })
}

function initBadge() {
  $('.immersup-badge').each(function () {
    var rgb = $(this).css('backgroundColor')
    var colors = rgb.match(/^rgb\((\d+),\s*(\d+),\s*(\d+)\)$/)

    var r = colors[1]
    var g = colors[2]
    var b = colors[3]

    var o = Math.round(((parseInt(r) * 299) + (parseInt(g) * 587) + (parseInt(b) * 114)) / 1000)

    if (o > 125) {
      $(this).css('color', 'black')
    } else {
      $(this).css('color', 'white')
    }
  })
}

function is_set(obj) {
  return obj !== null && obj !== undefined && obj !== "" && obj !== "None"
}

function formatDate(date, date_options = _dates_options, date_locale = _dates_locale) {
  return new Date(date).toLocaleString(date_locale, date_options)
}

function set_session_values(pagename, values) {
  var csrftoken = getCookie('csrftoken');

  $.ajax({
    beforeSend: function (request) {
      request.setRequestHeader("X-CSRFToken", csrftoken);
    },

    url: `/core/utils/set_session_values`,
    data: {
      pagename: pagename,
      values: JSON.stringify(values),
    },
    method: "POST",
    success: function (response) { },
    error: function (response) { }
  });
}

/*
Display a string with a limit and a tooltip with the full string
*/
function displayLongString(string, limit = 50, html = false) {
  // remove html tags from string
  let cleanedString = string.replace(/<[^>]*>/g, ' ')
  if (html && cleanedString.length > limit) {
    if (findBootstrapEnvironment() === 'xs' || findBootstrapEnvironment() === 'sm') {
      return string
    } else {
      return `<span data-toggle="tooltip" data-html="true" title="${string}">` + cleanedString.substring(0, limit) + '<span id="dots">...</span></span>'
    }
  }
  return cleanedString.length > limit ? cleanedString.substring(0, limit) + '...' : cleanedString
}

/*
Find the current environment based on the bootstrap display classes
*/
function findBootstrapEnvironment() {
  let envs = ['xs', 'sm', 'md', 'lg', 'xl'];

  let el = document.createElement('div');
  document.body.appendChild(el);

  let curEnv = envs.shift();

  for (let env of envs.reverse()) {
    el.classList.add(`d-${env}-none`);

    if (window.getComputedStyle(el).display === 'none') {
      curEnv = env;
      break;
    }
  }

  document.body.removeChild(el);
  return curEnv;
}

// Display and manage exit of the disabled referent notification modal
function open_notify_disability_modal(slot_id, modal_mode=false) {
  current_slot_id = slot_id
  modal_open = modal_mode;
  $('#modal_notify_disability').modal('show');

  // Wait for the modal to close (whatever the choice of the student)
  return new Promise(resolve =>
    $("#modal_notify_disability").on('hidden.bs.modal', () => {
      resolve();
    })
  );
}