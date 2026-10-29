// GLIDEPATH SPIKE TEST — does this Premiere build expose Bezier handle / ease data?
// HOW TO RUN: select ONE clip that has keyframes (e.g. Position or Scale) on the timeline,
// then run this file via the VS Code "ExtendScript Debugger" extension (target: Adobe Premiere Pro).
// OUTPUT: ~/Desktop/glidepath_spike_report.txt  — send that file back to me.

(function () {
    var out = [];
    function log(s) { out.push(s); }

    log("Premiere version: " + app.version);
    var seq = app.project.activeSequence;
    if (!seq) { log("NO ACTIVE SEQUENCE"); write(); return; }

    var sel = seq.getSelection();
    if (!sel || sel.length === 0) { log("NO CLIP SELECTED"); write(); return; }

    var clip = sel[0];
    log("Clip: " + clip.name);

    var re = /tangent|bezier|ease|influence|handle|speed|velocity|interp/i;
    var methodDumpDone = false;

    for (var c = 0; c < clip.components.length; c++) {
        var comp = clip.components[c];
        log("\nCOMPONENT [" + c + "] " + comp.displayName);
        for (var p = 0; p < comp.properties.numItems; p++) {
            var prop = comp.properties[p];
            var supports = false, keys = [];
            try { supports = prop.areKeyframesSupported(); } catch (e) {}
            try { if (supports && prop.isTimeVarying()) keys = prop.getKeys() || []; } catch (e) {}
            log("  - " + prop.displayName + " | keyframes supported: " + supports + " | key count: " + keys.length);

            if (keys.length > 0 && !methodDumpDone) {
                methodDumpDone = true;
                log("\n  === FULL API of a keyframed property (reflect) ===");
                try {
                    var ms = prop.reflect.methods;
                    for (var i = 0; i < ms.length; i++) log("   method: " + ms[i].name);
                    var ps = prop.reflect.properties;
                    for (var j = 0; j < ps.length; j++) log("   property: " + ps[j].name);
                } catch (e) { log("   reflect failed: " + e); }

                log("\n  === Names matching tangent/bezier/ease/handle/influence/speed ===");
                var hit = false;
                try {
                    var all = prop.reflect.methods.concat ? prop.reflect.methods : [];
                    for (var k = 0; k < prop.reflect.methods.length; k++) {
                        var nm = prop.reflect.methods[k].name;
                        if (re.test(nm)) { log("   >>> " + nm); hit = true; }
                    }
                    for (var m = 0; m < prop.reflect.properties.length; m++) {
                        var pn = prop.reflect.properties[m].name;
                        if (re.test(pn)) { log("   >>> " + pn); hit = true; }
                    }
                } catch (e) {}
                if (!hit) log("   (none found)");

                // Try reading interpolation type at first key
                try {
                    log("\n  Interp type @key0: " + prop.getKeyInterpolationTypeAtKey ? "method exists" : "n/a");
                } catch (e) {}
                try {
                    log("  Interp type @key0 value: " + prop.getInterpolationTypeAtKey(keys[0]));
                } catch (e) { log("  getInterpolationTypeAtKey: " + e); }
            }
        }
    }

    write();

    function write() {
        var f = new File(Folder.desktop.fsName + "/glidepath_spike_report.txt");
        f.open("w"); f.write(out.join("\n")); f.close();
        $.writeln("Report written to " + f.fsName);
    }
})();
