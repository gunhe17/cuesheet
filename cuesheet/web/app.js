// #
// 진입점 — URL 을 읽어 뷰를 고른다. 상태의 단일 출처는 주소창이다

import * as route from "./shell/route.js";
import * as view from "./shell/view.js";
import * as session from "./core/session.js";
import * as login from "./page/login.js";
import * as register from "./page/register.js";
import * as pick from "./page/pick.js";
import * as cuesheet from "./page/cuesheet.js";


// #
// resolve

function resolve() {
  const { name, params } = route.current();

  if (!session.read()?.token) {
    cuesheet.stop();
    view.show("login");
    return;
  }

  if (name === "cuesheet") {
    session.write({ ...session.read(), cuesheet_id: params.cuesheet_id });
    view.show("cuesheet");
    cuesheet.enter();
    return;
  }

  cuesheet.stop();
  view.show("pick");
  pick.enter();
}


// #
// wire

view.wire();
login.wire(after);
register.wire(after);
pick.wire();
cuesheet.wire();

route.onChange(resolve);
resolve();

function after() {
  route.go(route.path.home(), { replace: true });
  resolve();
}
