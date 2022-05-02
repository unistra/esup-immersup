window.onload = function () {
  let purge_modal = document.getElementById('purge_modal')
  let purge_submit = document.getElementById("submit_purge")
  let annual_purge_checker = document.getElementById("annual_purge_checker")

  $(purge_modal).dialog({
    autoOpen: false,
    modal: true,
    width: 500,
  })

  document.getElementById("purge_btn").addEventListener("click",function() {
    purge_submit.setAttribute("disabled", "")
    annual_purge_checker.value = ""
    $(purge_modal).dialog("open")
  })

  annual_purge_checker.addEventListener("input", (event) => {
      if ( event.target.value === verify_purge_text ) {
          purge_submit.removeAttribute("disabled")
          event.target.setAttribute("disabled", "")
      }
  })
}

