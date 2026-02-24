import {React, useState} from 'react'

function Login() {
  const [state, setState] = useState("login")
  const [name,setName] = useState("")
  const [email,setEmail] = useState("")
  const [password, setPassword] = useState("")

  const handleSubmit = async (e) => {
    e.preventDefault();
  }
  
  return (
    
    <div className="bg-white text-gray-500 max-w-96 mx-4 md:p-6 p-4 text-left text-sm rounded-xl shadow-[0px_0px_10px_0px] shadow-black/10">
        <h2 className="text-2xl font-semibold mb-6 text-center text-gray-800">{state === "login" ? "Welcome back" : "Sign Up"}</h2> 
        <form onSubmit={handleSubmit}>
          {state === "register" && (
              <input id="username" className="w-full bg-transparent border mt-1 mb-1 border-gray-500/30 outline-none rounded-full py-2.5 px-4" type="username" placeholder="Enter your username" required />
          )}
            <input id="email" className="w-full bg-transparent border my-3 border-gray-500/30 outline-none rounded-full py-2.5 px-4" type="email" placeholder="Enter your email" required />
            <input id="password" className="w-full bg-transparent border mt-1 border-gray-500/30 outline-none rounded-full py-2.5 px-4" type="password" placeholder="Enter your password" required />
            {state !== 'register'&& (
            <div className="text-right py-4">
                <a className="text-blue-600 underline" href="#">Forgot Password</a>
            </div>
            )}
            {state === 'register' ? (
              <button type="submit" className="w-full mb-3 mt-5 bg-purple-700 hover:bg-purple-800 py-2.5 rounded-full text-white">Create Account</button>

            ):(
              <button type="submit" className="w-full mb-3 bg-purple-700 hover:bg-purple-800 py-2.5 rounded-full text-white">Log in</button>
            )}
        </form>
        {state === "register" ? (
                <p className="text-center mt-4">
                    Already have account? <span onClick={() => setState("login")} className=" text-purple-700 cursor-pointer">Login</span>
                </p>
            ) : (
                <p className="text-center mt-4">
                    Don’t have an account? <span onClick={() => setState("register")} className=" text-purple-700 cursor-pointer">Signup</span>
                </p>
          )}

        {/* <button type="button" className="w-full flex items-center gap-2 justify-center mt-5 bg-black py-2.5 rounded-full text-white">
            <img className="h-4 w-4" src="https://raw.githubusercontent.com/prebuiltui/prebuiltui/main/assets/login/appleLogo.png" alt="appleLogo" />
            {state === "register" ? "Create" : "Login"} with Apple
        </button> */}
        <button type="button" className="w-full flex items-center gap-2 justify-center my-3 bg-white border border-gray-500/30 py-2.5 rounded-full text-gray-800">
            <img className="h-4 w-4" src="https://raw.githubusercontent.com/prebuiltui/prebuiltui/main/assets/login/googleFavicon.png" alt="googleFavicon" />
            {state === "register" ? "Create" : "Login"} with Google
        </button>
    </div>
);
}

export default Login