var test = [[3.2, 5.2],[2.4,8.2],[8.1,2.6],[5.6,6.4],[9.6,1.2],[9.4,4.5],[4.2,6.8]];

var limiteX = [0,10];
var limiteY = [0,10];

var nbColonne = 2;
var nbLigne = 2;
var result = [];
for (i=0; i<nbColonne; i++) {
    var ligne = [];
    for (j=0; j<nbLigne; j++) {
        ligne.push(0);
    }
    result[i] = ligne;
}
var tailleX = (limiteX[1]-limiteX[0])/nbColonne;
var tailleY = (limiteY[1]-limiteY[1])/nbLigne;
for (i = 0; i < test.length; i++) {
    X = Math.floor(test[i][0]/tailleX);
    Y = Math.floor(test[i][1]/tailleY);
    result[X][Y] += 1;
}