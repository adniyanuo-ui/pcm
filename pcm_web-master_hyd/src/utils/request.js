// src/utils/request.js
import axios from 'axios';
import {Message, Loading} from 'element-ui';
import router from "@/router"; // 如果使用 Element UI

// 创建 Axios 实例
const service = axios.create({
    baseURL: process.env.VUE_APP_BASE_API || '/api', // 基础 URL，根据环境配置
    timeout: 60000, // 请求超时时间
});

let loadingInstance;
let requestCount = 0;
// localStorage.setItem("token", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJ1c2VybmFtZSI6InRlc3QifQ.FHhvy4Ghj9vtOY4BUyZbne8UvFU091q0O90zXBo-fzU")
// localStorage.setItem("name", "test")
// 请求拦截器
service.interceptors.request.use(
    config => {
        // requestCount++;
        // if (requestCount === 1) {
        //     loadingInstance = Loading.service({ fullscreen: true });
        // }
        // 在请求发送之前做一些处理，例如添加 token
        const token = localStorage.getItem('token');
        if (token) {
            config.headers['Authorization'] = `Token ${token}`; // 根据你的认证方式设置
        }
        return config;
    },
    error => {
        // requestCount--;
        // if (requestCount === 0 && loadingInstance) {
        //     loadingInstance.close();
        // }
        // 处理请求错误
        Message.error("请求失败")
        // console.error('request error:', error);
        return Promise.reject(error);
    }
);

// 响应拦截器
service.interceptors.response.use(
    response => {
        // requestCount--;
        // if (requestCount === 0 && loadingInstance) {
        //     loadingInstance.close();
        // }

        // 对响应数据做一些处理
        const res = response.data;
        if (res instanceof Blob){
            return response
        }

        // 根据后端返回的状态码进行不同的处理
        if (res.code !== 200) { // 这里假设 200 为成功状态码，根据你的后端定义修改
            Message.error(res.msg || 'Error')

            // 示例：如果 token 过期，则跳转到登录页面
            if (res.code === 401) {
                // 清除 token 并跳转到登录页面
                localStorage.removeItem('token');
                router.push("/login");
                // location.href = '/login'; // 或使用 Vue Router 进行跳转
            }

            return Promise.reject(new Error(res.msg || 'Error'));
        }

        return res;
    },
    error => {
        // requestCount--;
        // if (requestCount === 0 && loadingInstance) {
        //     loadingInstance.close();
        // }
        // console.error('response error:', error);
        Message.error(error.message || '网络错误')
        return Promise.reject(error);
    }
);

export default service;
