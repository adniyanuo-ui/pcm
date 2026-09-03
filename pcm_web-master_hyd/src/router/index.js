import Vue from 'vue'
import VueRouter from 'vue-router'

Vue.use(VueRouter)

const routes = [
  {
    path: '/login',
    name: 'login',
    meta: {title: '登陆'},
    component: () => import(/* webpackChunkName: "about" */ '../views/login.vue')
  },
  {
    path: '/register',
    name: 'register',
    meta: {title: '注册'},
    component: () => import(/* webpackChunkName: "about" */ '../views/register.vue')
  },
  {
    path: '/',
    name: 'welcome',
    meta: {title: '欢迎'},
    component: () => import(/* webpackChunkName: "about" */ '../views/Welcome.vue')
  },
  {
    path: '/question',
    name: 'question',
    meta: {title: '答题'},
    component: () => import(/* webpackChunkName: "about" */ '../views/Question.vue')
  },
  {
    path: '/result',
    name: 'result',
    meta: {title: '结果'},
    component: () => import(/* webpackChunkName: "about" */ '../views/result.vue')
  },
]

const router = new VueRouter({
  mode: 'hash',
  base: process.env.BASE_URL,
  routes
})

export default router
