from gurobipy import GRB, Model, quicksum
import random
import json
import os.path
from os import path


if __name__ == "__main__":

    if path.exists("params.json"):
        model = Model()
        with open("params.json", "r") as file:
            data = json.load(file)

        # INDICES Y PARAMETROS
        n = data["n"] # Recolectores
        m = data["m"] # Costas
        K = data["K"] # Puntos de encuentro
        R = data["R"] # Centros de reciclaje
        T = data["T"] # Dias de la semana

        i = [x for x in range(n)] # Indice recolectores
        j = [x for x in range(m)] # Indice costas
        k = [x for x in range(K)] # Indice puntos de encuentro
        r = [x for x in range(R)] # Indice centros de reciclaje
        t = [x for x in range(T)] # Indice dias de la semana

        V = data["V"] # Cantidad disponible de vehiculos de transporte de personas
        C = data["C"] # Cantidad disponible de vehiculos de transporte de plástico
        Cv = data["Cv"] # Capacidad de transporte de personas por bus
        Cc = data["Cc"] # Capacidad de transporte de plástico por camión
        P = data["P"] # Cantidad promedio de unidades de plastico que recolecta 1 persona en 1 día
        B = data["B"] # Total de unidades de plastico a recolectar en la semana (meta)

        E_jt = data["E_jt"] # llegada de plastico a costa j en dia t
        def Q(j, t):  # Cantidad de plastico en costa j el dia t.
            if t == 0:
                return 0
            else:
                r =  Q(j, t- 1) - x[t - 1, j] * P + E_jt[j][t]
                return r

        L_jkt = data["L_jkt"] # Costo de transporte de buses desde ubicacion k hasta costa j el dia t
        H_jrt = data["H_jrt"] # Costo de transporte de camiones desde costa j hasta centro de reciclaje r el dia t
        a_tji = data["a_tji"] # Disponibilidad de persona i para ir a costa j el dia t

        # VARIABLES DE DECISION
        x = {} # x_tj
        y = {} # y_tjk
        z = {} # z_tjk
        s = {} # s_trj

        for t in range(T):
            for j in range(m):
                # Cantidad de personas que recolectan plástico en costa j el dia t:
                x[t, j] = model.addVar(vtype=GRB.INTEGER, name="x_[{}][{}]".format(t, j))
                for k in range(K):
                    # Cantidad de personas que van desde ubicación k hasta costa j el día t:
                    y[t, j, k] = model.addVar(vtype=GRB.INTEGER, name="y_[{}][{}][{}]".format(t, j, k))
                    # Cantidad de buses que transportan personas desde ubicación k hasta costa j el día t:
                    z[t, j, k] = model.addVar(vtype=GRB.INTEGER, name="z_[{}][{}][{}]".format(t, j, k))
                for r in range(R):
                    # Cantidad de camiones que transportan plástico desde costa j hasta centro r el día t:
                    s[t, r, j] = model.addVar(vtype=GRB.INTEGER, name="s_[{}][{}][{}]".format(t, r, j))

        model.update()

        # OBJETIVO
        objective = quicksum(2 * z[t, j, k] for t in range(T) for j in range(m) for k in range(K)) + quicksum(2 * H_jrt[j][r][t] * s[t, r, j] for t in range(T) for r in range(R) for j in range(m))
        model.setObjective(objective, GRB.MINIMIZE)

        # RESTRICCIONES

        ## Meta de recolección:
        model.addConstr(B <= quicksum(P * x[t, j] for t in range(T) for j in range(m)), name="R1")


        ## Conservacion de plástico:
        for t in range(1, T):
            for j in range(m):
                model.addConstr(x[t - 1, j] <= (Q(j, t- 1) - Q(j, t) + E_jt[j][t])/P, name="R2_{}{}".format(t, j))

        ## Control de cantidades de personas enviadas:
        for t in range(T):
            for j in range(m):
                model.addConstr(Q(j, t) >= P * x[t, j], name="R3_{}{}".format(t, j))

        ## Cantidad limitada de camiones
        for t in range(T):
            model.addConstr(quicksum(s[t, r, j] for r in range(R) for j in range(m)) <= C, name="R4_{}".format(t))

        ## Cantidad limitada de buses
        for t in range(T):
            model.addConstr(quicksum(z[t, j, k] for j in range(m) for k in range(K)) <= V, name="R5_{}".format(t))

        ## Capacidad de camiones
        for t in range(T):
            for j in range(m):
                model.addConstr(P * x[t, j] <= Cc * quicksum(s[t, r, j] for r in range(R)), name="R6_{}{}".format(t, j))

        ## Capacidad de buses
        for t in range(T):
            for j in range(m):
                for k in range(K):
                    model.addConstr(y[t, j, k] <= Cv * z[t, j, k], name="R7_{}{}{}".format(t, j, k))

        ## Consistencia en cantidad de personas:
        for t in range(T):
            for j in range(m):
                model.addConstr(x[t, j] == quicksum(y[t, j, k] for k in range(K)), name="R8_{}{}".format(t, j))


        ## Disponibilidad de personas:
        for t in range(T):
            for j in range(m):
                model.addConstr(x[t, j] <= quicksum(a_tji[t][j][i] for i in range(n)), name="R9_{}{}".format(t, j))


        ## No negatividad
        for t in range(T):
            for j in range(m):
                model.addConstr(x[t, j] >= 0, name="R10_{}{}".format(t, j))
                for k in range(K):
                    model.addConstr(z[t, j, k] >= 0, name="R11_{}{}{}".format(t, j, k))
                    model.addConstr(y[t, j, k] >= 0, name="R12_{}{}{}".format(t, j, k))
                for r in range(R):
                    model.addConstr(s[t, r, j] >= 0, name="R13_{}{}{}".format(t, j, r))

        # SOLUCIÓN
        model.optimize()
        print("Numero de soluciones: {}".format(model.solCount))
        model.printAttr("X")
        model.write("out.sol")
        print("Valor optimo:", model.getObjective().getValue())
