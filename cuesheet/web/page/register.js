// #
// register — 가입 후 그대로 로그인 상태로 들어간다

import * as api from "../core/api.js";
import * as form from "../core/form.js";
import * as session from "../core/session.js";

export function wire(onSuccess) {
  form.bind("form-register", "register-notice", async (input) => {
    await api.post("/users", {
      login_id: input.login_id,
      name: input.name,
      pin: input.pin,
    });

    const user = await api.post("/users/session", {
      login_id: input.login_id,
      pin: input.pin,
    });

    session.write({ token: user.token, name: user.name });
    form.reset("form-register");
    onSuccess();
  });
}
