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
  $(document).on('showFeedback', function(event, ...messages) {
    var $target = $(event.target).empty()
    messages.forEach(function(element) {
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

    var o = Math.round(((parseInt(r) * 299) + (parseInt(g) * 587) + (parseInt(b) * 114)) /1000)

    if(o > 125) {
      $(this).css('color', 'black')
    }else{
      $(this).css('color', 'white')
    }
  })
}

function is_set(obj) {
  return obj !== null && obj !== undefined && obj !== "" && obj !== "None"
}