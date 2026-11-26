// Only explicit clicks reach this seam. Native sender actions and validated
// window routing stay in the original service. Never execute arbitrary hints.
.pragma library
.import "Security.js" as Security
function admittedArgv(argv) {
  if (!Array.isArray(argv) || argv.length !== 2
      || argv[0] !== "/usr/bin/xdg-open") return null
  var safe = Security.safeExternalUrl(argv[1])
  return safe ? ["/usr/bin/xdg-open", safe] : null
}
function runArgv(argv) {
  var safe = admittedArgv(argv)
  return safe ? Qt.openUrlExternally(safe[1]) : false
}
