function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie != '') {
        let cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            let cookie = jQuery.trim(cookies[i]);
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) == (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

window.onload = function () {
  let purge_modal = document.getElementById('purge_modal')
  let purge_submit = document.getElementById("submit_purge")
  let annual_purge_checker = document.getElementById("annual_purge_checker")
  let purge_btn = document.getElementById("purge_btn")

  const csrfToken = getCookie('csrftoken')
  const csrfHeaders = new Headers({
      "X-CSRFToken": csrfToken,
      "Content-Type": "application/json"
  })

  $(purge_modal).dialog({
    autoOpen: false,
    modal: true,
    width: 500,
  })

  if (purge_btn !== null) {
    purge_btn.addEventListener("click", function () {
      purge_submit.setAttribute("disabled", "")
      annual_purge_checker.removeAttribute("disabled")
      annual_purge_checker.value = ""
      document.getElementById("fetch_content").innerText = ""
      $(purge_modal).dialog("open")
    })

    annual_purge_checker.addEventListener("input", (event) => {
      if (event.target.value === verify_purge_text) {
        purge_submit.removeAttribute("disabled")
        event.target.setAttribute("disabled", "")
      }
    })

    purge_submit.addEventListener("click", (event) => {
      const content = document.getElementById("fetch_content")
      content.innerHTML = "<br/></br.><p class='center'>" + gettext("Command running ...") + "</p>"
      purge_submit.setAttribute("disabled", "")

      fetch("/api/commands/annual_purge/",{
        method: "POST",
        headers: csrfHeaders,
      })
      .then(response => response.json())
      .then(data => {
        if (data.ok) {
          content.innerHTML = "<br/><ul class='messagelist'><li class='success'>" + gettext("Purge finished") + "</li></ul>"
          setTimeout(() => {
            window.location.reload()
          }, 3000)
        } else {
          content.innerHTML = "<br/><ul class='messagelist'><li class='error'>" + data.msg + "</li></ul>"
        }
      })
    })
  }
}

