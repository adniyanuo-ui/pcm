import axios from 'axios'
// import Qs from 'qs'
import router from '@/router/index'
import store from '@/store/index'
import { Message } from 'element-ui'

const toLogin = () => {
    store.dispatch('user/logout').then(() => {
        router.push({
            name: 'login'
        })
    })
    // router.push({
    //     path: '/login',
    //     query: {
    //         redirect: router.currentRoute.fullPath
    //     }
    // })
}

const api = axios.create({
    baseURL: process.env.VUE_APP_API_ROOT,
    timeout: 10000,
    // responseType: 'json'
    // withCredentials: true
})

api.interceptors.request.use(
    config => {
        // console.log("config", store.state, config)
        config.headers['Authorization'] = `Token ${store.state.user.token}`;
        return config
    }
)

api.interceptors.response.use(
    response => {
        // 根据后端返回的状态码进行不同的处理
        if (response.config.responseType === "stream"){
            return response
        }
        if (response.data.code !== 200) { // 这里假设 200 为成功状态码，根据你的后端定义修改
            Message.error(response.data.msg || 'Error')

            // 示例：如果 token 过期，则跳转到登录页面
            if (response.data.code === 401) {
                // 清除 token 并跳转到登录页面
                toLogin()
                // localStorage.removeItem('token');
                // location.href = '/'; // 或使用 Vue Router 进行跳转
            }

            return Promise.reject(new Error(response.data.msg || 'Error'));
        }else {
            Message.success(response.data.msg || "Success")
        }
        return Promise.resolve(response.data)
    },
    error => {
        return Promise.reject(error)
    }
)

export default api;
